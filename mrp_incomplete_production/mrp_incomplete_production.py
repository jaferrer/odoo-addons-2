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

from openerp import fields, models, api, workflow, _
from collections import OrderedDict
import openerp
from openerp.tools import float_compare
from openerp.osv import osv
from datetime import *
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT




class procurement_rule2(models.Model):
    _inherit = 'procurement.rule'

    child_loc_id = fields.Many2one('stock.location', string="Child location", help="Source and destination locations of the automatically generated manufacturing order")

class procurement_order2(models.Model):
    _inherit = 'procurement.order'

    def _prepare_mo_vals(self, cr, uid, procurement, context=None):
        result = super(procurement_order2, self)._prepare_mo_vals(cr, uid, procurement, context=None)
        if procurement.rule_id.child_loc_id.id:
            result['child_location_id'] = procurement.rule_id.child_loc_id.id
        return result


class product_produce(models.Model):
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

    production_id = fields.Many2one('mrp.production', string="Related Manufacturing Order", default=_get_default_production_id, readonly=True)
    child_production_product_id = fields.Many2one('product.product', default=_get_default_product_id, string='Product of the child Manufacturing Order')
    child_src_loc_id = fields.Many2one('stock.location', string="Child source location", default=_get_default_src_location, help="If this field is empty, the child of this Manufacturing Order will have the same source location as his parent. If it is filled, the child will have this location as source location.")
    child_dest_loc_id = fields.Many2one('stock.location', string="Child destination location", default=_get_default_dest_location, help="If this field is empty, the child of this Manufacturing Order will have the same destination location as his parent. If it is filled, the child will have this location as destination location.")
    production_all_available = fields.Boolean(string='True if the raw material of the related Manufacturing Order is entirely available', default=_get_default_availability, readonly=True)
    product_different = fields.Boolean(string="True if the child product is different from the parent one", compute="is_product_different")

    @api.one
    @api.depends('child_production_product_id')
    def is_product_different(self):
        order=False
        c = self.env.context
        if c and c.get("active_id"):
            order = self.env['mrp.production'].browse(c.get("active_id"))
        self.product_different = False
        if order and order.product_id != self.child_production_product_id:
            self.product_different = True



class product_line2(models.Model):
    _inherit = 'mrp.production.product.line'
    parent_production_id = fields.Many2one('mrp.production', string="This Manufacturing Order has generated a child with this move as raw material", readonly=True)

class mrp_production2(models.Model):
    _inherit = "mrp.production"

    backorder_id = fields.Many2one('mrp.production', string="Parent Manufacturing Order", readonly=True)
    child_location_id = fields.Many2one('stock.location', string="Children Location", help="If this field is empty, potential children of this Manufacturing Order will have the same source and destination locations as their parent. If it is filled, the children will have this location as source and destination locations.")
    child_order_id = fields.Many2one('mrp.production', string="Child Manufacturing Order", compute="get_child_order_id", readonly=True, store=False)
    child_move_ids = fields.One2many('mrp.production.product.line', 'parent_production_id', string="Not consumed products", readonly=True)
    one_available = fields.Boolean(string="True if one product is available", compute="get_availability", readonly=True, store=False)
    left_products = fields.Boolean(string="True if child_move_ids is not empty", compute="get_child_moves", readonly=True, store=False)

    @api.one
    def get_child_order_id(self):
        self.child_order_id = False
        list_ids = self.env['mrp.production'].search([('backorder_id', '=', self.id)])
        if len(list_ids) == 1:
            self.child_order_id = list_ids[0]

    @api.one
    def get_availability(self):
        self.one_available = False
        if self.move_lines:
            for move in self.move_lines:
                if move.state == 'assigned':
                    self.one_available = True
                    break

    @api.one
    def get_child_moves(self):
        self.left_products = True
        if not self.child_move_ids:
            self.left_products = False

    def _calculate_qty(self, cr, uid, production, product_qty=0.0, context=None):
        consume_lines = super(mrp_production2, self)._calculate_qty(cr, uid, production)
        # print 'consume', consume_lines
        # print 'moves :'
        for item in production.move_lines:
            # print item.product_id.name, item.product_qty, item.state, item.product_id.type
            if item.product_id.id not in [x['product_id'] for x in consume_lines]:
                # attention : numéro de lot !
                consume_lines += [{'lot_id': False, 'product_id': item.product_id.id, 'product_qty': item.product_qty}]
                # quel lot veut-on mettre ?
        # print 'new_consume', consume_lines
        # print 'calcul des quantites'
        list_to_remove = []
        for item in consume_lines:
            local_product_id = item['product_id']
            # print 'nouveau produit courant', self.pool.get('product.product').browse(cr, uid, local_product_id, context=context).name
            total = sum([x.product_qty for x in production.move_lines if x.product_id.id == local_product_id and x.state == 'assigned'])
            if total != 0:
                item['product_qty'] = total
            else:
                list_to_remove += [item]
        for move in list_to_remove:
            consume_lines.remove(move)
        # if len(consume_lines) == 0:
        #     raise osv.except_osv(_('Error!'),_("Yon cannot produce if no product is available."))
        return consume_lines







    @api.one
    def get_locations_product(self):
        produce = self.env['mrp.product.produce'].search([('production_id', '=', self.id)])
        # print produce
        result = []
        result += [produce.child_production_product_id]
        result += [produce.child_src_loc_id]
        result += [produce.child_dest_loc_id]
        result += [produce.product_different]
        # print 'result', result
        return result

    def action_produce(self, cr, uid, production_id, production_qty, production_mode, wiz=False, context=None):
        production = self.pool.get('mrp.production').browse(cr, uid, production_id, context=context)
        # print('===============action_produce================ for MO: ', production.name)
        list_cancelled_moves1 = []
        for item in production.move_lines2:
            list_cancelled_moves1 += [item]
        # print('cancelled', list_cancelled_moves1)
        result = super(mrp_production2, self).action_produce(cr, uid, production_id, production_qty, production_mode, wiz=False, context=None)
        list_cancelled_moves = []
        for move in production.move_lines2:
            if move.state == 'cancel' and move not in list_cancelled_moves1:
                list_cancelled_moves += [move]
        # print('cancelled2', list_cancelled_moves)
        if len(list_cancelled_moves)!= 0:
            items = production.get_locations_product()[0]
            # print 'items', items
            production_data = {
                'product_id': items[0].id,
                'product_qty': production.product_qty,
                'product_uom': production.product_uom.id,
                'location_src_id': items[1].id,
                'location_dest_id': items[2].id,
                'date_planned': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'bom_id': production.bom_id.id,
                'company_id': production.company_id.id,
                'backorder_id': production.id,
            }
            production.state = 'done'
            new_production_id = self.create(cr, openerp.SUPERUSER_ID, production_data)
            # print production_data
            # print new_production_id
            new_production = self.pool.get('mrp.production').browse(cr, uid, new_production_id, context=context)
            # print new_production
            if items[3]:
                new_production._make_production_produce_line(new_production)
            for item in list_cancelled_moves:
                # print 'new item', item.product_id.name, item.product_qty
                product_line_data = {
                    'name': production.name,
                    'product_id': item.product_id.id,
                    'product_qty': item.product_qty,
                    'product_uom': item.product_uom.id,
                    'product_uos_qty': item.product_uos_qty,
                    'product_uos': item.product_uos.id,
                    'parent_production_id': production.id,
                }
                new_product_line_id = self.pool.get('mrp.production.product.line').create(cr, openerp.SUPERUSER_ID, product_line_data)
                new_production_line = self.pool.get('mrp.production.product.line').browse(cr, uid, new_product_line_id, context=context)
                new_production.product_lines = new_production.product_lines +  new_production_line

            new_production.update_moves()
            new_production.state = 'confirmed'
        # print('=====================================step_workflow=================================')
        self.step_workflow(cr, uid, [production_id], context)
        return result


    @api.multi
    def button_update(self):
        self.ensure_one()
        try:
            if not self.backorder_id:
                self._action_compute_lines()
                self.update_moves()
        except AttributeError:
            print('button update skipped')