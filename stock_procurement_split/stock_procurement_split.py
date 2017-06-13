# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def split(self, move, qty, restrict_lot_id=False, restrict_partner_id=False):
        split_move_id = super(StockMove, self).split(move, qty, restrict_lot_id, restrict_partner_id)
        move = self.search([('id', '=', split_move_id)])
        proc = move.procurement_id
        if proc:
            new_proc = proc.copy({
                'state': 'running',
                'product_qty': move.product_uom_qty,
                'move_dest_id': move.move_dest_id.id,
            })
            proc.product_qty -= move.product_uom_qty
            move.procurement_id = new_proc
            new_proc.check()
            proc.check()
        return split_move_id
