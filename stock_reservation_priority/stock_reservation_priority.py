# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api, fields
from openerp.tools import float_compare


class StockReservationPriorityStockMove(models.Model):
    _inherit = 'stock.move'

    priority = fields.Selection(copy=False)

    @api.multi
    def action_assign(self):
        to_assign_ids = self and self.ids or []
        moves_to_assign = self.search([('id', 'in', to_assign_ids)], order='priority desc, date asc, id asc')
        read_moves_to_assign = moves_to_assign.read(
            ['id', 'location_id', 'product_id', 'priority', 'date', 'product_qty'], load=False)
        for move_to_assign in read_moves_to_assign:
            prec = self.env['product.product'].browse(move_to_assign['product_id']).uom_id.rounding
            quants_on_move = self.env['stock.quant'].search([('reservation_id', '=', move_to_assign['id'])])
            quants_on_move = quants_on_move.read(['qty'], load=False)
            reserved_qty = sum([quant['qty'] for quant in quants_on_move])
            needed_qty = move_to_assign['product_qty'] - reserved_qty
            if float_compare(needed_qty, 0, precision_rounding=prec) > 0:
                available_quants = self.env['stock.quant']. \
                    search([('location_id', 'child_of', move_to_assign['location_id']),
                            ('product_id', '=', move_to_assign['product_id']),
                            ('reservation_id', '=', False)])
                available_quants = available_quants.read(['qty'], load=False)
                available_qty = sum([quant['qty'] for quant in available_quants])
                if float_compare(needed_qty, available_qty, precision_rounding=prec) > 0:
                    reserved_quants = self.env['stock.quant']. \
                        search([('location_id', 'child_of', move_to_assign['location_id']),
                                ('product_id', '=', move_to_assign['product_id']),
                                ('reservation_id', '!=', False)])
                    reserved_quants = reserved_quants.read(['reservation_id'], load=False)
                    reservation_ids = [quant['reservation_id'] for quant in reserved_quants]
                    running_moves_ordered_reverse = self.env['stock.move']. \
                        search([('id', 'in', reservation_ids),
                                '|', ('priority', '<', move_to_assign['priority']),
                                '&', ('priority', '=', move_to_assign['priority']),
                                ('date', '>', move_to_assign['date'])],
                               order='priority asc, date desc, id desc')
                    running_moves_ordered_reverse = running_moves_ordered_reverse.read(['id', 'product_qty'], load=False)
                    moves_to_unreserve = []
                    for move_to_unreserve in running_moves_ordered_reverse:
                        if float_compare(available_qty, needed_qty, precision_rounding=prec) >= 0:
                            break
                        if move_to_unreserve['id'] == move_to_assign['id']:
                            continue
                        move_quants = self.env['stock.quant'].search([('reservation_id', '=', move_to_unreserve['id'])])
                        move_quants = move_quants.read(['qty'], load=False)
                        move_reserved_qty = sum([quant['qty'] for quant in move_quants])
                        available_qty += move_reserved_qty
                        moves_to_unreserve += [move_to_unreserve['id']]
                        if float_compare(available_qty, needed_qty, precision_rounding=prec) > 0:
                            to_assign_ids += [move_to_unreserve['id']]
                    if moves_to_unreserve:
                        moves_to_unreserve = self.env['stock.move'].browse(moves_to_unreserve)
                        moves_to_unreserve.do_unreserve()
        return super(StockReservationPriorityStockMove, moves_to_assign).action_assign()
