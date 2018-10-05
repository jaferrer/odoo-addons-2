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

from openerp import models, api, exceptions, _

ERROR_MSG = u"This is a Technical error message\n"
u"If you see this message thanks to contact your technical service and keep this message in the screen\n"
u"Technical information:\n"
u"Quant moved: %s\n"
u"Reserved by the move: %s\n"
u"Want to reserved by the move : %s\n"
u"Reason: %s"


class QuantOriginStockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.multi
    def write(self, vals):
        move_to_check = []
        for rec in self:
            reservation_id = vals.get('reservation_id', rec.reservation_id.id)
            if rec.reservation_id and rec.reservation_id.id != reservation_id:
                move_to_check.append((rec.reservation_id.id, rec.id))
        super(QuantOriginStockQuant, self).write(vals)
        reservation_id_vals = vals.get('reservation_id')
        for move_id, quant_id in move_to_check:
            move = self.env['stock.move'].browse(move_id)
            if move.state == 'assigned':
                raise exceptions.except_orm(_(u"Error!"),
                                            _(ERROR_MSG) %
                                            (quant_id, move_id, reservation_id_vals, u"Still assigned"))
            if not move.reserved_quant_ids and move.partially_available:
                raise exceptions.except_orm(_(u"Error!"),
                                            _(ERROR_MSG) %
                                            (quant_id, move_id, reservation_id_vals, u"Still partially available"))
