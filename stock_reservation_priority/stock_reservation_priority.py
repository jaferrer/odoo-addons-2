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

    @api.model
    def get_reserved_quants_query(self, product_id, location_id, picking_id):
        location = self.env['stock.location'].search([('id', '=', location_id)])
        res = """
            SELECT sq.reservation_id
            FROM stock_quant sq
                LEFT JOIN stock_location sl ON sq.location_id = sl.id
                LEFT JOIN stock_move sm ON sq.reservation_id = sm.id
            WHERE sq.product_id = %s
                AND sl.parent_left >= %s
                AND sl.parent_left < %s
                AND sq.reservation_id IS NOT NULL
        """
        params = (product_id, location.parent_left, location.parent_right)
        if picking_id:
            res += " AND (sm.picking_id != %s OR sm.picking_id IS NULL)"
            params += (picking_id,)
        return res, params

    @api.multi
    def action_assign(self):
        to_assign_ids = self and self.ids or []
        moves_to_assign = self.search([('id', 'in', to_assign_ids)], order='priority desc, date asc, id asc')
        read_moves_to_assign = moves_to_assign.read(
            ['id', 'location_id', 'product_id', 'priority', 'date', 'product_qty', 'picking_id'], load=False)
        reserved_quant_qties = {}
        for move_to_assign in read_moves_to_assign:
            prec = self.env['product.product'].browse(move_to_assign['product_id']).uom_id.rounding
            quants_on_move = self.env['stock.quant'].read_group([('reservation_id', '=', move_to_assign['id'])],
                                                                ['qty', 'reservation_id'], ['reservation_id'])
            reserved_qty = quants_on_move and quants_on_move[0]['qty'] or 0
            needed_qty = move_to_assign['product_qty'] - reserved_qty
            if float_compare(needed_qty, 0, precision_rounding=prec) > 0:
                available_quants = self.env['stock.quant']. \
                    read_group([('location_id', 'child_of', move_to_assign['location_id']),
                                ('product_id', '=', move_to_assign['product_id']),
                                ('reservation_id', '=', False)], ['qty', 'reservation_id'], ['reservation_id'])
                available_qty = available_quants and available_quants[0]['qty'] or 0
                available_qty -= reserved_quant_qties.get(move_to_assign['product_id'], 0)
                reserved_quant_qties.setdefault(move_to_assign['product_id'], 0)
                reserved_quant_qties[move_to_assign['product_id']] += needed_qty
                if float_compare(needed_qty, available_qty, precision_rounding=prec) > 0:
                    quants_query, quants_params = self.get_reserved_quants_query(move_to_assign['product_id'],
                                                                                 move_to_assign['location_id'],
                                                                                 move_to_assign['picking_id'])
                    self.env.cr.execute(quants_query, quants_params)
                    reservation_ids = [r[0] for r in self.env.cr.fetchall()]
                    running_moves_ordered_reverse = self.env['stock.move']. \
                        search_read([('id', 'in', reservation_ids),
                                     '|', ('priority', '<', move_to_assign['priority']),
                                     '&', ('priority', '=', move_to_assign['priority']),
                                     ('date', '>', move_to_assign['date'])], ['id', 'product_qty'],
                                    order='priority asc, date desc, id desc')
                    moves_to_unreserve_ids = []
                    for move_to_unreserve in running_moves_ordered_reverse:
                        if float_compare(available_qty, needed_qty, precision_rounding=prec) >= 0:
                            break
                        if move_to_unreserve['id'] == move_to_assign['id']:
                            continue
                        move_quants = self.env['stock.quant'].read_group(
                            [('reservation_id', '=', move_to_unreserve['id'])],
                            ['qty', 'reservation_id'], ['reservation_id'])
                        move_reserved_qty = move_quants and move_quants[0]['qty'] or 0
                        available_qty += move_reserved_qty
                        moves_to_unreserve_ids.append(move_to_unreserve['id'])
                    if moves_to_unreserve_ids:
                        moves_to_unreserve = self.env['stock.move'].browse(moves_to_unreserve_ids)
                        moves_to_unreserve.do_unreserve()
        return super(StockReservationPriorityStockMove, moves_to_assign).action_assign()
