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

from openerp import models, api


class StockReservationPriorityStockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def action_assign(self):
        moves_to_assign = self.env['stock.move']
        to_assign_ids = self and self.ids or []
        for move_to_assign in self.search([('id', 'in', to_assign_ids)], order='priority asc, date desc, id desc'):
            qty_available = sum([quant.qty for quant in self.env['stock.quant'].
                                search([('location_id', 'child_of', move_to_assign.location_id.id),
                                        ('product_id', '=', move_to_assign.product_id.id),
                                        ('reservation_id', '=', False)])])
            running_moves_ordered_reverse = self.env['stock.move']. \
                search([('location_id', 'child_of', move_to_assign.location_id.id),
                        ('product_id', '=', move_to_assign.product_id.id),
                        '|', ('reserved_quant_ids', '!=', False),
                        ('id', '=', move_to_assign.id)],
                       order='priority asc, date desc, id desc')
            for move_to_unreserve in running_moves_ordered_reverse:
                if move_to_unreserve == move_to_assign or qty_available >= move_to_assign.product_uom_qty:
                    break
                qty_available += move_to_unreserve.product_uom_qty
                move_to_unreserve.do_unreserve()
                if qty_available > move_to_assign.product_uom_qty:
                    moves_to_assign = moves_to_assign + move_to_unreserve
        moves_to_assign = self.search([('id', 'in', self.ids + (moves_to_assign and moves_to_assign.ids or []))],
                                      order='priority desc, date asc, id asc')
        return super(StockReservationPriorityStockMove, moves_to_assign).action_assign()
