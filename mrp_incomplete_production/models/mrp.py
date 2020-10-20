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

from collections import OrderedDict
from datetime import datetime

from openerp import fields, models, api, exceptions, _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import float_compare, float_round


class IncompleteProductionProductLine(models.Model):
    _inherit = 'mrp.production.product.line'

    parent_production_id = fields.Many2one('mrp.production', readonly=True,
                                           string=u"This Manufacturing Order has generated a child with this move "
                                                  u"as raw material")


class IncompeteProductionMrpProduction(models.Model):
    _inherit = 'mrp.production'

    backorder_id = fields.Many2one('mrp.production', string=u"Parent Manufacturing Order", readonly=True)
    child_location_id = fields.Many2one('stock.location', string=u"Children Location",
                                        help=u"If this field is empty, potential children of this Manufacturing Order "
                                             u"will have the same source and destination locations as their parent. If "
                                             u"it is filled, the children will have this location as source "
                                             u"and destination locations.")
    child_order_id = fields.Many2one('mrp.production', string=u"Child Manufacturing Order",
                                     compute="_get_child_order_id", readonly=True, store=False)
    child_move_ids = fields.One2many('mrp.production.product.line', 'parent_production_id',
                                     string=u"Not consumed products", readonly=True)
    left_products = fields.Boolean(string=u"True if child_move_ids is not empty", compute="_get_child_moves",
                                   readonly=True, store=False)
    warehouse_id = fields.Many2one('stock.warehouse', string=u"Warehouse", compute='_compute_warehouse_id', store=True)

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
    @api.depends('location_src_id')
    def _compute_warehouse_id(self):
        for rec in self:
            rec.warehouse_id = rec.location_src_id and \
                rec.sudo().location_src_id.get_warehouse(rec.location_src_id) or False

    @api.model
    def _get_consumed_data(self, production):
        ''' returns a dictionary containing for each raw material of the given production, its quantity already
        consumed (in the raw material UoM)

        Overridden here to remove cancel moves from the calculation
        '''
        consumed_data = {}
        # Calculate already consumed qtys
        for consumed in production.move_lines2:
            if consumed.scrapped or consumed.state == "cancel":
                continue
            if not consumed_data.get(consumed.product_id.id, False):
                consumed_data[consumed.product_id.id] = 0
            consumed_data[consumed.product_id.id] += consumed.product_qty
        return consumed_data

    @api.model
    def _calculate_qty(self, production, product_qty=0.0):
        produced_qty = self._get_produced_qty(production)
        list_keys = []
        new_consume_lines = []
        if not product_qty:
            product_qty = self.env['product.uom']._compute_qty(production.product_uom.id, production.product_qty,
                                                               production.product_id.uom_id.id) - produced_qty
        production_qty = self.env['product.uom']._compute_qty(production.product_uom.id, production.product_qty,
                                                              production.product_id.uom_id.id)
        scheduled_qty = OrderedDict()
        for scheduled in production.product_lines:
            if scheduled.product_id.type == 'service':
                continue
            qty = self.env['product.uom']._compute_qty(scheduled.product_uom.id, scheduled.product_qty,
                                                       scheduled.product_id.uom_id.id)
            if scheduled_qty.get(scheduled.product_id.id):
                scheduled_qty[scheduled.product_id.id] += qty
            else:
                scheduled_qty[scheduled.product_id.id] = qty
        consume_lines = super(IncompeteProductionMrpProduction, self)._calculate_qty(production, product_qty)
        for item in consume_lines:
            key = (item['product_id'], item['lot_id'])
            if key not in list_keys:
                sched_product_qty = scheduled_qty[key[0]]
                total_consume = ((product_qty + produced_qty) * sched_product_qty / production_qty)
                reserved_quants = self.env['stock.quant'].search([('reservation_id', 'in', production.move_lines.ids),
                                                                  ('product_id', '=', key[0]),
                                                                  ('lot_id', '=', key[1] or False)])
                reserved_qty = sum([quant.qty for quant in reserved_quants])
                final_qty = min(reserved_qty, total_consume)
                if float_compare(final_qty, 0,
                                 self.env['decimal.precision'].precision_get('Product Unit of Measure')) != 0:
                    new_consume_lines += [{'product_id': key[0], 'lot_id': key[1], 'product_qty': final_qty}]
                list_keys += [key]
        return new_consume_lines

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

    @api.multi
    def sanitize_not_available_raw_moves(self):
        moves_to_detach = self.env['stock.move']
        for rec in self:
            moves_to_check = self.env['stock.move'].search([('id', 'in', rec.move_lines.ids),
                                                            ('state', '!=', 'assigned')])
            for move in moves_to_check:
                prec = move.product_id.uom_id.rounding
                reserved_quants = move.reserved_quant_ids
                if not reserved_quants:
                    moves_to_detach |= move
                    continue
                reserved_qty = sum([quant.qty for quant in reserved_quants])
                if float_compare(reserved_qty, move.product_qty, precision_rounding=prec) < 0:
                    new_move_id = move.split(move, float_round(move.product_qty - reserved_qty, precision_rounding=prec))
                    new_move = self.env['stock.move'].search([('id', '=', new_move_id)])
                    move.action_assign()
                    moves_to_detach |= new_move
        moves_to_detach.write({'raw_material_production_id': False})
        return moves_to_detach

    @api.multi
    def cancel_service_procs(self):
        procurements_to_cancel = self.env['procurement.order']. \
            search([('move_dest_id.raw_material_production_id', 'in', self.ids),
                    ('state', 'not in', ['cancel', 'done'])])
        if procurements_to_cancel:
            procurements_to_cancel.cancel()

    @api.multi
    def action_cancel(self):
        result = super(IncompeteProductionMrpProduction, self).action_cancel()
        self.cancel_service_procs()
        return result

    @api.model
    def action_produce(self, production_id, production_qty, production_mode, wiz=False):
        if not wiz or not wiz.create_child and (not wiz.return_raw_materials or not wiz.return_location_id):
            return super(IncompeteProductionMrpProduction, self.with_context(cancel_procurement=True)). \
                action_produce(production_id, production_qty, production_mode, wiz=wiz)

        production = self.browse(production_id)
        list_cancelled_moves_1 = production.move_lines2
        moves_to_detach = production.sanitize_not_available_raw_moves()
        # To call super, all the raw material moves are available.
        result = super(IncompeteProductionMrpProduction, self.with_context(cancel_procurement=True)). \
            action_produce(production_id, production_qty, production_mode, wiz=wiz)
        list_cancelled_moves = production.move_lines2. \
            filtered(lambda move: move.state == 'cancel' and move not in list_cancelled_moves_1)
        if not production.move_created_ids:
            list_cancelled_moves += moves_to_detach
        if len(list_cancelled_moves) != 0 and wiz and wiz.create_child:
            production_data = production._get_child_order_data(wiz)
            production.action_production_end()
            new_production = self.env['mrp.production'].create(production_data)
            for move in list_cancelled_moves:
                product_line_data = production._get_child_order_product_line_data(move)
                new_production_line = self.env['mrp.production.product.line'].create(product_line_data)
                new_production.product_lines = new_production.product_lines + new_production_line
            new_production.signal_workflow('button_confirm')
        if len(list_cancelled_moves) != 0 and wiz.return_raw_materials and wiz.return_location_id:
            quants_to_return = self.env['stock.quant']
            for move in list_cancelled_moves:
                quants_to_return |= self.env['stock.quant'].search([('location_id', '=', move.location_id.id),
                                                                    ('product_id', '=', move.product_id.id)]). \
                    filtered(lambda q: any([m.move_dest_id.raw_material_production_id ==
                                            move.raw_material_production_id for m in q.history_ids]))
            return_picking_type = self.env.context.get('force_return_picking_type') or \
                move.get_return_picking_id()
            if not return_picking_type:
                raise exceptions.except_orm(_("Error!"), _("Impossible to determine return picking type"))
            return_picking = quants_to_return.move_to(dest_location=wiz.return_location_id,
                                                      picking_type=return_picking_type)
            return_picking.write({'origin': production.name})
        # Let's cancel old service moves if the MO is totally produced
        if moves_to_detach:
            moves_to_detach.write({'raw_material_production_id': production.id})
        if not production.move_created_ids:
            production.cancel_service_procs()
            for move in moves_to_detach:
                if move.state not in ['done', 'cancel']:
                    move.action_cancel()
        return result

    @api.model
    def _make_production_produce_line(self, production):
        if not production.backorder_id or production.backorder_id.product_id != production.product_id:
            return super(IncompeteProductionMrpProduction, self)._make_production_produce_line(production)
        else:
            return []

    @api.multi
    def action_assign(self):
        result = super(IncompeteProductionMrpProduction, self).action_assign()
        for order in self:
            if any([move.reserved_quant_ids for move in order.move_lines]):
                order.signal_workflow('moves_ready')
        return result
