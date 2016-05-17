# -*- coding: utf8 -*-
#
#    Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from openerp import fields, models, api, exceptions, _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class IncompleteProductionProductLine(models.Model):
    _inherit = 'mrp.production.product.line'

    parent_production_id = fields.Many2one('mrp.production', readonly=True,
                                           string="This Manufacturing Order has generated a child with this move "
                                                  "as raw material")


class IncompeteProductionMrpProduction(models.Model):
    _inherit = 'mrp.production'

    backorder_id = fields.Many2one('mrp.production', string="Parent Manufacturing Order", readonly=True)
    child_location_id = fields.Many2one('stock.location', string="Children Location",
                                        help="If this field is empty, potential children of this Manufacturing Order "
                                             "will have the same source and destination locations as their parent. If "
                                             "it is filled, the children will have this location as source "
                                             "and destination locations.")
    child_order_id = fields.Many2one('mrp.production', string="Child Manufacturing Order",
                                     compute="_get_child_order_id", readonly=True, store=False)
    child_move_ids = fields.One2many('mrp.production.product.line', 'parent_production_id',
                                     string="Not consumed products", readonly=True)
    left_products = fields.Boolean(string="True if child_move_ids is not empty", compute="_get_child_moves",
                                   readonly=True, store=False)
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse", compute='_compute_warehouse_id', store=True)

    @api.multi
    def _get_child_order_id(self):
        for rec in self:
            child_order_id = False
            list_ids = self.env['mrp.production'].search([('backorder_id', '=', rec.id)])
            if len(list_ids) >= 1:
                child_order_id = list_ids[0]
            rec.child_order_id = child_order_id

    @api.multi
    def _get_child_moves(self):
        for rec in self:
            rec.left_products = bool(rec.child_move_ids)

    @api.multi
    @api.depends('location_dest_id')
    def _compute_warehouse_id(self):
        for rec in self:
            rec.warehouse_id = rec.location_dest_id and rec.location_dest_id.get_warehouse(rec.location_dest_id)

    @api.multi
    @api.depends('location_dest_id')
    def _compute_warehouse_id(self):
        for rec in self:
            warehouse_id = rec.location_dest_id and rec.sudo().location_dest_id.get_warehouse(rec.location_dest_id) or False
            rec.warehouse_id = warehouse_id

    @api.model
    def _calculate_qty(self, production, product_qty=0.0):
        consume_lines = super(IncompeteProductionMrpProduction, self)._calculate_qty(production, product_qty)
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

    @api.multi
    def _get_child_order_data(self, wiz):
        self.ensure_one()
        return {
            'product_id': wiz.child_production_product_id.id,
            'product_qty': self.product_qty,
            'product_uom': self.product_uom.id,
            'location_src_id': wiz.child_src_loc_id.id,
            'location_dest_id': wiz.child_dest_loc_id.id,
            'date_planned': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'bom_id': self.bom_id.id,
            'company_id': self.company_id.id,
            'backorder_id': self.id,
        }

    @api.multi
    def _get_child_order_product_line_data(self, cancelled_move):
        self.ensure_one()
        return {
            'name': self.name,
            'product_id': cancelled_move.product_id.id,
            'product_qty': cancelled_move.product_qty,
            'product_uom': cancelled_move.product_uom.id,
            'product_uos_qty': cancelled_move.product_uos_qty,
            'product_uos': cancelled_move.product_uos.id,
            'parent_production_id': self.id,
        }

    @api.model
    def action_produce(self, production_id, production_qty, production_mode, wiz=False):
        production = self.browse(production_id)
        list_cancelled_moves_1 = production.move_lines2
        result = super(IncompeteProductionMrpProduction, self.with_context(cancel_procurement=True)). \
            action_produce(production_id, production_qty, production_mode, wiz=wiz)
        list_cancelled_moves = production.move_lines2. \
            filtered(lambda move: move.state == 'cancel' and move not in list_cancelled_moves_1)
        if len(list_cancelled_moves) != 0 and wiz.create_child:
            production_data = production._get_child_order_data(wiz)
            production.action_production_end()
            new_production = self.env['mrp.production'].create(production_data)
            if wiz.product_different:
                new_production._make_production_produce_line(new_production)
            for move in list_cancelled_moves:
                product_line_data = production._get_child_order_product_line_data(move)
                new_production_line = self.env['mrp.production.product.line'].create(product_line_data)
                new_production.product_lines = new_production.product_lines + new_production_line
            new_production.signal_workflow('button_confirm')
        if len(list_cancelled_moves) != 0 and wiz.return_raw_materials and wiz.return_location_id:
            picking_to_change_origin = self.env['stock.picking']
            quants_to_return = self.env['stock.quant']
            for move in list_cancelled_moves:
                quants_to_return |= self.env['stock.quant'].search([('location_id', '=', move.location_id.id),
                                                                    ('product_id', '=', move.product_id.id)]). \
                    filtered(lambda q: any([m.move_dest_id.raw_material_production_id == \
                                            move.raw_material_production_id for m in q.history_ids]))
            return_picking_type = self.env.context.get('force_return_picking_type') or \
                                  move.get_return_picking_id()
            if not return_picking_type:
                raise exceptions.except_orm(_("Error!"), _("Impossible to determine return picking type"))
            return_moves = quants_to_return.move_to(dest_location=wiz.return_location_id,
                                                    picking_type_id=return_picking_type)
            for item in return_moves:
                picking_to_change_origin |= item.picking_id
            picking_to_change_origin.write({'origin': production.name})
        return result

    @api.multi
    def button_update(self):
        self.ensure_one()
        if not self.backorder_id:
            self._action_compute_lines()
            self.update_moves()

    @api.multi
    def action_assign(self):
        result = super(IncompeteProductionMrpProduction, self).action_assign()
        for order in self:
            for move in order.move_lines:
                if move.state == 'assigned':
                    order.signal_workflow('moves_ready')
                    break
        return result
