# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from openerp import fields, models, api
from itertools import groupby


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def _make_merge_key(self):
        """Overridden here so that we can group PO with different picking_types."""
        self.ensure_one()
        return self.partner_id.id, self.currency_id.id


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    partner_dest_id = fields.Many2one('res.partner', string=u"Delivery Address",
                                      help=u"Specify a delivery address here if this line is to be sent directly to a "
                                      u"customer (dropshipping). Lines without partner_dest_id will follow the value "
                                      u"process defined in the order.")

    @api.model
    def _get_group_keys(self, order, line, picking=False):
        """Define the key that will be used to group. The key should be
        defined as a tuple of dictionaries, with each element containing a
        dictionary element with the field that you want to group by. This
        method is designed for extensibility, so that other modules can add
        additional keys or replace them by others."""
        partner = line.partner_dest_id
        if partner:
            location_dest = self.env.ref('stock.stock_location_customers')
            picking_type = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', False),
                ('code', '=', 'incoming'),
                ('default_location_src_id', '=', self.env.ref('stock.stock_location_suppliers').id),
                ('default_location_dest_id', '=', location_dest.id),
            ], limit=1)
        else:
            picking_type = order.picking_type_id
            location_dest = picking_type.default_location_dest_id
        key = ({'partner_dest_id': (partner, picking_type, location_dest)},)
        return key

    @api.model
    def _first_picking_copy_vals(self, key, lines):
        """The data to be copied to new pickings is updated with data from the
        grouping key.  This method is designed for extensibility, so that
        other modules can store more data based on new keys."""
        vals = {'move_lines': []}
        for key_element in key:
            if 'partner_dest_id' in key_element.keys():
                vals.update({
                    'partner_dest_id': key_element['partner_dest_id'][0].id,
                    'picking_type_id': key_element['partner_dest_id'][1].id,
                    'location_dest_id': key_element['partner_dest_id'][2].id,
                })
        return vals

    @api.multi
    def _create_stock_moves(self, picking):
        """Group the receptions in one picking per group key"""
        moves = self.env['stock.move']
        # Group the order lines by group key
        order_lines = sorted(self,
                             key=lambda l: self._get_group_keys(
                                 l.order_id, l, picking=picking))
        dest_groups = groupby(order_lines, lambda l: self._get_group_keys(
            l.order_id, l, picking=picking))

        # If a picking is provided, use it for the first group only
        if picking:
            first_picking = picking
            key, lines = dest_groups.next()
            po_lines = self.env['purchase.order.line']
            for line in list(lines):
                po_lines += line
            picking._update_picking_from_group_key(key)
            moves += super(PurchaseOrderLine, po_lines)._create_stock_moves(
                first_picking)
        else:
            first_picking = False

        for key, lines in dest_groups:
            # If a picking is provided, clone it for each key for modularity
            if picking:
                copy_vals = self._first_picking_copy_vals(key, lines)
                picking = first_picking.copy(copy_vals)
            po_lines = self.env['purchase.order.line']
            for line in list(lines):
                po_lines += line
            moves += super(PurchaseOrderLine, po_lines)._create_stock_moves(
                picking)

        for move in moves:
            move.partner_id = move.picking_id.partner_dest_id

        return moves


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    partner_dest_id = fields.Many2one('res.partner', string=u"Delivery Address")

    @api.multi
    def _update_picking_from_group_key(self, key):
        """The picking is updated with data from the grouping key.
        This method is designed for extensibility, so that other modules
        can store more data based on new keys."""
        for rec in self:
            for key_element in key:
                if 'partner_dest_id' in key_element.keys():
                    rec.write({
                        'partner_dest_id': key_element['partner_dest_id'][0].id,
                        'picking_type_id': key_element['partner_dest_id'][1].id,
                        'location_dest_id': key_element['partner_dest_id'][2].id,
                    })
        return False


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def _prepare_purchase_order_line(self, po, supplier):
        self.ensure_one()
        res = super(ProcurementOrder, self)._prepare_purchase_order_line(po, supplier)
        res.update({
            'partner_dest_id': self.partner_dest_id.id,
        })
        return res
