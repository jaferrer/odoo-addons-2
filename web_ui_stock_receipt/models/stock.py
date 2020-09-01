# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from openerp import models, api


class WebUiError(Exception):
    pass


class StockPickingReceipt(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def get_receipt_grouped_pickings(self):
        list_owners = []
        picking_receiptes = self.env['stock.picking'].search([
            ('state', 'in', ('assigned', 'partially_available')),
            ('picking_type_id', '=', self.env.ref('stock.picking_type_in').id),
        ], order='owner_id, create_date desc')

        for picking in picking_receiptes:

            if not list_owners or list_owners[-1]['id'] != picking.owner_id.id:
                owner = {
                    'id': picking.owner_id and picking.owner_id.id or "",
                    'name': picking.owner_id and picking.owner_id.name or "Autres",
                    'stock_pickings': []
                }
                list_owners.append(owner)

            list_owners[-1]['stock_pickings'].append({
                'id': picking.id,
                'name': picking.name,
                'date': picking.date,
            })

        return list_owners

    @api.model
    def get_receipt_move_lines(self, picking_id):
        list_stock_pickings = []
        move_lines = self.env['stock.pack.operation'].search([
            ('picking_id', '=', picking_id),
            ('product_id', '!=', False)
        ])

        for move_line in move_lines:
            product_infos = move_line.product_id.web_ui_get_product_info_one()

            list_stock_pickings.append({
                'id': move_line.id,
                'product': product_infos,
                'quantity': move_line.product_qty - move_line.qty_done,
                'product_uom': move_line.product_uom_id.name
            })

        return list_stock_pickings

    @api.multi
    def do_validate_receipt(self, product_infos):
        self.ensure_one()
        edited_spo = self.env['stock.pack.operation']

        for product_info in product_infos:
            # Le spo de notre stock.picking
            product_pack_ops = self.pack_operation_product_ids.filtered(lambda x: x.product_id.id == product_info['id'])

            # Les reliquats du produit dans les spo des autres stock.picking
            if product_info['quantity'] > product_pack_ops.product_qty:
                product_pack_ops |= self.env['stock.pack.operation'].search([
                    ('product_id', '=', product_info['id']),
                    ('picking_id.picking_type_code', '=', 'incoming'),
                    ('picking_id.state', '=', 'assigned'),
                    ('picking_id.backorder_id', '!=', None),
                ], order="create_date asc")

            edited_spo |= self.distribute_qty_in_pack_ops(product_pack_ops, product_info['quantity'])

        for picking in edited_spo.mapped('picking_id'):
            self.env['stock.backorder.confirmation'].create({'pick_id': picking.id}).process()

        result = {}
        for spo in edited_spo:
            if not result.get(spo.picking_id.id):
                result[spo.picking_id.id] = {
                    'picking_id': spo.picking_id.id,
                    'picking_name': spo.picking_id.display_name,
                    'pack_operations': []
                }

            result[spo.picking_id.id]['pack_operations'].append({
                'id': spo.id,
                'product': spo.product_id.display_name,
                'product_qty': spo.product_qty,
                'qty_done': spo.qty_done
            })

        return result.values()

    @api.model
    def distribute_qty_in_pack_ops(self, spo_stack, qty, edited_spo=None):
        if not edited_spo:
            edited_spo = self.env['stock.pack.operation']

        # Stop when all quantity is distributed or when there is no spo in the stack left
        if (qty == 0 and edited_spo) or not spo_stack:
            # If there is quantity left but not spo in the stack, first item takes it all
            if qty > 0 and edited_spo:
                edited_spo[0].qty_done += qty
            return edited_spo

        current_spo = spo_stack[0]
        if qty > current_spo.product_qty:
            qty_to_set = current_spo.product_qty
            qty_remaining = qty - current_spo.product_qty
        else:
            qty_to_set = qty
            qty_remaining = 0
        current_spo.qty_done = qty_to_set
        edited_spo |= current_spo

        return self.distribute_qty_in_pack_ops(spo_stack[1:], qty_remaining, edited_spo)


# On utilise le nom StockMoveLine pour parler des stock.pack.operation pour
# volontairement garder plus de similarites entre le module v9 et v12
class StockMoveLineScanReceipt(models.Model):
    _inherit = 'stock.pack.operation'

    @api.multi
    def do_clear_siblings_move_lines_receipt(self):
        """
        Permet de supprimer les move lines identiques de quantité réservée et réalisée à 0. Car on peut avoir deux fois
        la même si on quitte l'application au milieu d'une ligne.
        """
        self.ensure_one()
        empty_move_line_siblings = self.picking_id.pack_operation_product_ids.filtered(
            lambda x: x.product_qty == 0 and
            x.qty_done == 0 and
            x.product_id == self.product_id and
            x.location_id == self.location_id
        )
        empty_move_line_siblings[1:].unlink()
