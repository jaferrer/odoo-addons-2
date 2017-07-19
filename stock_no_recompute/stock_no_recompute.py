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

from openerp import osv, models, api, _
from openerp.tools import SUPERUSER_ID, float_compare


class StockQuant(models.Model):

    _inherit = "stock.quant"

    @api.model
    def quants_reserve(self, quants, move, link=False):
        """Overridden here to remove recompute_pack_op modification"""
        toreserve = self.env['stock.quant']
        reserved_availability = move.reserved_availability
        # split quants if needed
        for quant, qty in quants:
            if qty <= 0.0 or (quant and quant.qty <= 0.0):
                raise osv.except_osv(_('Error!'), _('You can not reserve a negative quantity or a negative quant.'))
            if not quant:
                continue
            self._quant_split(quant, qty)
            toreserve |= quant
            reserved_availability += quant.qty
        # reserve quants
        toreserve.sudo().write({'reservation_id': move.id})
        # check if move'state needs to be set as 'assigned'
        rounding = move.product_id.uom_id.rounding
        dict_move = {}
        if float_compare(reserved_availability, move.product_qty, precision_rounding=rounding) == 0 and \
                move.state in ('confirmed', 'waiting'):
            dict_move['state'] = 'assigned'
        elif float_compare(reserved_availability, 0, precision_rounding=rounding) > 0 and not move.partially_available:
            dict_move['partially_available'] = True
        if dict_move:
            move.write(dict_move)

    @api.model
    def quants_unreserve(self, move):
        related_quants = move.reserved_quant_ids
        if related_quants:
            if move.partially_available:
                move.partially_available = False
            related_quants.sudo().write({'reservation_id': False})


class StockPicking(models.Model):

    _inherit = "stock.picking"

    @api.multi
    def force_assign(self):
        """ Changes state of picking to available if moves are confirmed or waiting.
        @return: True
        """
        for pick in self:
            moves = pick.move_lines.filtered(lambda m: m.state in ['confirmed', 'waiting'])
            moves.force_assign()
        return True
