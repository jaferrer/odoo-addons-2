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

class mrp_production2(models.Model):
    _inherit = "mrp.production"

    backorder_id = fields.Many2one('mrp.production', string="Parent Manufacturing Order")
    child_location_source_id = fields.Many2one('stock.location', string="Children Source Location", help="If this field is empty, potential children of this Manufacturing Order will have the same source locations as their parent. If it is filled, the children will have this location as source locations.")
    child_location_destination_id = fields.Many2one('stock.location', string="Children Destination Location", help="If this field is empty, potential children of this Manufacturing Order will have the same destination locations as their parent. If it is filled, the children will have this location as destination locations.")

    # def force_production(self, cr, uid, ids, *args):
    #     """ Assigns products.
    #     @param *args: Arguments
    #     @return: True
    #     """
    #     move_obj = self.pool.get('stock.move')
    #     for order in self.browse(cr, uid, ids):
    #         # move_obj.force_assign(cr, uid, [x.id for x in order.move_lines])
    #         production = self.pool.get('mrp.production')
    #         if production.test_ready(cr, uid, [order.id]):
    #             workflow.trg_validate(uid, 'mrp.production', order.id, 'moves_ready', cr)
    #         else:
    #             # if len([x for x in production.move_lines if x.state == 'assigned']) == 0:
    #             #     raise osv.except_osv(_('Error!'),_("Unable to adapt the initial balance (negative value)."))
    #             # else:
    #             print('Achtnug! Certains produits ne sont pas disponibles')
    #             workflow.trg_validate(uid, 'mrp.production', order.id, 'moves_ready', cr)
    #     return True





    def _calculate_qty(self, cr, uid, production, product_qty=0.0, context=None):
        consume_lines = super(mrp_production2, self)._calculate_qty(cr, uid, production)
        print 'consume', consume_lines
        print 'moves :'
        for item in production.move_lines:
            print item.product_id.name, item.product_qty, item.state, item.product_id.type
            if item.product_id.id not in [x['product_id'] for x in consume_lines]:
                consume_lines += [{'lot_id': False, 'product_id': item.product_id.id, 'product_qty': item.product_qty}]
                # quel lot veut-on mettre ?
        print 'new_consume', consume_lines
        print 'calcul des quantites'
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
        if len(consume_lines) == 0:
            raise osv.except_osv(_('Error!'),_("Yon cannot produce if no product is available."))
        return consume_lines










    def action_produce(self, cr, uid, production_id, production_qty, production_mode, wiz=False, context=None):
        print('===============new action_produce================')
        production = self.pool.get('mrp.production').browse(cr, uid, production_id, context=context)
        list_cancelled_moves1 = []
        for item in production.move_lines2:
            list_cancelled_moves1 += [item]
        result = super(mrp_production2, self).action_produce(cr, uid, production_id, production_qty, production_mode, wiz=False, context=None)
        list_cancelled_moves = []
        for move in production.move_lines2:
            if move.state == 'cancel' and move not in list_cancelled_moves1:
                list_cancelled_moves += [move]
        print 'cancelled', list_cancelled_moves
        if len(list_cancelled_moves)!= 0:
            # empty_bom_data = {
            #     'name': "empty_bom",
            #     'type': "normal",
            #     'product_tmpl_id': production.bom_id.product_tmpl_id.id,
            #     'product_id': production.bom_id.product_id.id,
            #     'product_qty': production.bom_id.product_qty,
            #     'product_uom': production.bom_id.product_uom.id,
            #     'product_efficiency': production.bom_id.product_efficiency
            # }
            # # new bom for this product : à reprendre pour mettre juste les produits dont on a besoin pour l'OF reliquat (?)
            # empty_bom = self.pool.get('mrp.bom').create(cr, openerp.SUPERUSER_ID, empty_bom_data)






            if production.child_location_source_id:
                location1 = production.child_location_source_id
            else:
                location1 = production.location_src_id
            if production.child_location_destination_id:
                location2 = production.child_location_destination_id
            else:
                location2 = production.location_dest_id
            production_data = {
                'product_id': production.product_id.id,
                'product_qty': production.product_qty,
                'product_uom': production.product_uom.id,
                'location_src_id': location1.id,
                'location_dest_id': location2.id,
                'date_planned': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'bom_id': production.bom_id.id,
                'company_id': production.company_id.id,
                'backorder_id': production.id,
                'child_location_source_id': production.child_location_source_id.id,
                'child_location_destination_id': production.child_location_destination_id.id,
            }
            production.state = 'done'
            new_production_id = self.create(cr, openerp.SUPERUSER_ID, production_data)
            print production_data
            print new_production_id
            new_production = self.pool.get('mrp.production').browse(cr, uid, new_production_id, context=context)
            print new_production
            for item in list_cancelled_moves:
                new_production.move_lines = new_production.move_lines + item
                item.name = new_production.name
                item.origin = new_production.name
                item.state='draft'
                item.action_confirm()
                print item.product_id.name, item.product_qty, item.state
            new_production.state = 'confirmed'
            for move in new_production.move_lines2:
                new_production_line_data = {
                    'name': new_production.name,
                    'product_id': move.product_id.id,
                    'product_qty': move.product_qty,
                    'product_uom': move.product_uom.id,
                    'product_uos_qty': move.product_uos_qty,
                    'product_uos': move.product_uos.id,
                    'production_id': new_production.id,
                }
                new_production_line_id = self.pool.get('mrp.production.product.line').create(cr, openerp.SUPERUSER_ID, new_production_line_data)
                new_production_line = self.pool.get('mrp.production.product.line').browse(cr, uid, new_production_line_id, context=context)
                print 'new line', new_production_line.product_id.name, new_production_line.product_qty
                print new_production.product_lines
                move.state='draft'
                move.action_confirm()
            print('=============================================================')
        return result

    @api.multi
    def button_update(self):
        self.ensure_one()
        try:
            if not self.backorder_id:
                self._action_compute_lines()
                self.update_moves()
        except AttributeError:
            print('youpi')

    # def action_production_end(self, cr, uid, ids, context=None):
    #     print('===============wooooooow================')
    #     result = super(mrp_production2, self).action_production_end(cr, uid, ids)
    #     return result

    # @api.multi
    # def check_availability_and_produce(self):
    #     number_moves_assigned = len([x for x in self.move_lines if x.state == 'assigned'])
    #     number_moves = len([x for x in self.move_lines])
    #     print('===============================================================')
    #     if number_moves == 0:
    #         print('no articles needed!')
    #         raise osv.except_osv(_('Error!'),_("Yon cannot produce if no product is needed."))
    #     if number_moves_assigned == 0:
    #         print('no article available!')
    #         raise osv.except_osv(_('Error!'),_("Yon cannot produce if no product is available."))
    #     if number_moves_assigned != 0 and number_moves_assigned != number_moves:
    #         print('all articles are not available !')
    #         # self.action_produce()
