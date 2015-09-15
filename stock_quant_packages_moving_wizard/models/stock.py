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

from openerp import models, fields, api
from copy import copy


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.multi
    def move_to(self, dest_location, picking_type_id, move_items=False):
        move_recordset = self.env['stock.move']
        for item in self:
            new_move = self.env['stock.move'].create({
                'name': 'Move %s to %s' % (item.product_id.name, dest_location.name),
                'product_id': item.product_id.id,
                'location_id': item.location_id.id,
                'location_dest_id': dest_location.id,
                'product_uom_qty': item.qty if not move_items else move_items[item.id].qty,
                'product_uom': item.product_id.uom_id.id,
                'date_expected': fields.Datetime.now(),
                'date': fields.Datetime.now(),
                'picking_type_id': picking_type_id.id
            })
            new_move.action_confirm()
            self.quants_reserve([(item, new_move.product_uom_qty)], new_move)
            
            move_recordset=move_recordset | new_move
                
        if move_recordset :
            picking=move_recordset[0].picking_id
            picking.do_prepare_partial()
            packops = picking.pack_operation_ids
            packops.write({'location_dest_id': dest_location.id})
            picking.do_transfer()
        
        return move_recordset