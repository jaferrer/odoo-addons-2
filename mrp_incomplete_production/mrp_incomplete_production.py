# -*- coding: utf8 -*-
#
# Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from datetime import datetime

from openerp import fields, models, api
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class procurement_rule2(models.Model):
    _inherit = 'procurement.rule'

    child_loc_id = fields.Many2one('stock.location', string="Child location", help="Source and destination locations of"
                                                                    " the automatically generated manufacturing order")


class procurement_order2(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _prepare_mo_vals(self,procurement):
        result = super(procurement_order2, self)._prepare_mo_vals(procurement)
        if procurement.rule_id.child_loc_id.id:
            result['child_location_id'] = procurement.rule_id.child_loc_id.id
        return result


class product_produce(models.TransientModel):
    _inherit = 'mrp.product.produce'

    def _get_default_production_id(self):
        order=False
        c = self.env.context
        if c and c.get("active_id"):
            order = self.env['mrp.production'].browse(c.get("active_id"))
        return order

    def _get_default_src_location(self):
        order=False
        c = self.env.context
        if c and c.get("active_id"):
            order = self.env['mrp.production'].browse(c.get("active_id"))
        if order:
            if order.child_location_id:
                return order.child_location_id
            else:
                return order.location_src_id
        else:
            return False

    def _get_default_dest_location(self):
        order=False
        c = self.env.context
        if c and c.get("active_id"):
            order = self.env['mrp.production'].browse(c.get("active_id"))
        if order:
            if order.child_location_id:
                return order.child_location_id
            else:
                return order.location_dest_id
        else:
            return False

    def _get_default_product_id(self):
        order=False
        c = self.env.context
        if c and c.get("active_id"):
            order = self.env['mrp.production'].browse(c.get("active_id"))
        if order:
            return order.product_id
        return order

    def _get_default_availability(self):
        order=False
        c = self.env.context
        if c and c.get("active_id"):
            order = self.env['mrp.production'].browse(c.get("active_id"))
        if order:
            for move in order.move_lines:
                if move.state != 'assigned':
                    return False
        return True

    production_id = fields.Many2one('mrp.production', string="Related Manufacturing Order",
                                    default=_get_default_production_id, readonly=True)
    child_production_product_id = fields.Many2one('product.product', default=_get_default_product_id,
                                                  string='Product of the child Manufacturing Order')
    child_src_loc_id = fields.Many2one('stock.location', string="Child source location",
            default=_get_default_src_location,
            help="If this field is empty, the child of this Manufacturing Order will have the same source location as "
                 "his parent. If it is filled, the child will have this location as source location.")
    child_dest_loc_id = fields.Many2one('stock.location', string="Child destination location",
                                        default=_get_default_dest_location, help="If this field is empty, the child of"
            " this Manufacturing Order will have the same destination location as his parent. If it is filled, the "
            "child will have this location as destination location.")
    production_all_available = fields.Boolean(string='True if the raw material of the related Manufacturing Order is '
                                              'entirely available', default=_get_default_availability, readonly=True)
    product_different = fields.Boolean(string="True if the child product is different from the parent one",
                                       compute="_is_product_different")

    @api.one
    @api.depends('child_production_product_id')
    def _is_product_different(self):
        order=False
        c = self.env.context
        if c and c.get("active_id"):
            order = self.env['mrp.production'].browse(c.get("active_id"))
        self.product_different = False
        if order and order.product_id != self.child_production_product_id:
            self.product_different = True


class product_line2(models.Model):
    _inherit = 'mrp.production.product.line'

    parent_production_id = fields.Many2one('mrp.production',
                string="This Manufacturing Order has generated a child with this move as raw material", readonly=True)


class mrp_production2(models.Model):
    _inherit = "mrp.production"

    backorder_id = fields.Many2one('mrp.production', string="Parent Manufacturing Order", readonly=True)
    child_location_id = fields.Many2one('stock.location', string="Children Location",
        help="If this field is empty, potential children of this Manufacturing Order will have the same source and "
             "destination locations as their parent. If it is filled, the children will have this location as source "
             "and destination locations.")
    child_order_id = fields.Many2one('mrp.production', string="Child Manufacturing Order",
                                     compute="_get_child_order_id", readonly=True, store=False)
    child_move_ids = fields.One2many('mrp.production.product.line', 'parent_production_id',
                                     string="Not consumed products", readonly=True)
    left_products = fields.Boolean(string="True if child_move_ids is not empty", compute="_get_child_moves",
                                   readonly=True, store=False)

    @api.one
    def _get_child_order_id(self):
        child_order_id = False
        list_ids = self.env['mrp.production'].search([('backorder_id', '=', self.id)])
        if len(list_ids) >= 1:
            child_order_id = list_ids[0]
        self.child_order_id = child_order_id

    @api.one
    def _get_child_moves(self):
        self.left_products = bool(self.child_move_ids)

    @api.model
    def _calculate_qty(self, production, product_qty=0.0):
        #TODO: supprimer argument inutile ?
        consume_lines = super(mrp_production2, self)._calculate_qty(production)
        list_to_remove = []
        for item in consume_lines:
            local_product_id = item['product_id']
            total = sum([x.product_qty for x in production.move_lines if x.product_id.id == local_product_id
                                                                                        and x.state == 'assigned'])
            if total != 0:
                item['product_qty'] = total
            else:
                list_to_remove += [item]
        for move in list_to_remove:
            consume_lines.remove(move)
        return consume_lines

    @api.model
    def action_produce(self, production_id, production_qty, production_mode, wiz=False):
        production = self.browse(production_id)
        list_cancelled_moves1 = []
        for item in production.move_lines2:
            list_cancelled_moves1 += [item]
        result = super(mrp_production2, self.with_context(cancel_procurement=True)).action_produce(production_id, production_qty, production_mode, wiz=wiz)
        list_cancelled_moves = []
        for move in production.move_lines2:
            if move.state == 'cancel' and move not in list_cancelled_moves1:
                list_cancelled_moves += [move]
        if len(list_cancelled_moves) != 0:
            production_data = {
                'product_id': wiz.child_production_product_id.id,
                'product_qty': production.product_qty,
                'product_uom': production.product_uom.id,
                'location_src_id': wiz.child_src_loc_id.id,
                'location_dest_id': wiz.child_dest_loc_id.id,
                'date_planned': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'bom_id': production.bom_id.id,
                'company_id': production.company_id.id,
                'backorder_id': production.id,
            }
            production.action_production_end()
            new_production = self.env['mrp.production'].create(production_data)
            if wiz.product_different:
                new_production._make_production_produce_line(new_production)
            for item in list_cancelled_moves:
                product_line_data = {
                    'name': production.name,
                    'product_id': item.product_id.id,
                    'product_qty': item.product_qty,
                    'product_uom': item.product_uom.id,
                    'product_uos_qty': item.product_uos_qty,
                    'product_uos': item.product_uos.id,
                    'parent_production_id': production.id,
                }
                new_production_line = self.env['mrp.production.product.line'].create(product_line_data)
                new_production.product_lines = new_production.product_lines +  new_production_line
            new_production.signal_workflow('button_confirm')
        return result

    @api.multi
    def button_update(self):
        self.ensure_one()
        if not self.backorder_id:
            self._action_compute_lines()
            self.update_moves()

    @api.multi
    def action_assign(self):
        super(mrp_production2, self).action_assign()
        for order in self:
            for move in order.move_lines:
                if move.state == 'assigned':
                    order.signal_workflow('moves_ready')
                    break
