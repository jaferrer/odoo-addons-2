# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api, exceptions, _

class stock_picking_performance_improved(models.Model):
    inherit = 'stock.picking'

    @api.multi
    def action_assign(self):
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        Overridden here to improve performance when there are a great number of moves
        @return: True
        """
        for pick in self:
            # First confirm the picking if it is not already
            if pick.state == 'draft':
                self.action_confirm()
            # We get all quants in the picking's source location that are not reserved yet
            quants = self.env['stock.quant'].search([('location_id','child_of',pick.location_id.id),
                                                     ('reservation_id','=',False)])
            # We create a dict with the quantities of each product to reserve
            product_qties = {}
            for quant in quants:
                if quant.product_id in product_qties:
                    product_qties[quant.product_id] += quant.qty
                else:
                    product_qties[quant.product_id] = quant.qty
            # We iterate on each product and quantities to reserve to get the moves to assign
            to_assign_moves = self.env['stock.move']
            for product, qty_todo in product_qties.iteritems():
                # Filter moves on the product
                moves = pick.move_lines.filtered(lambda m: m.product_id == product)
                # Get only the needed number of moves to assign the qty to do and add them to to_assign_moves.
                qty_left = qty_todo
                for move in moves:
                    to_assign_moves = to_assign_moves | move
                    qty_left -= move.product_qty
                    if qty_left <= 0:
                        break
            if not to_assign_moves:
                raise exceptions.except_orm(_('Warning!'), _('Nothing to check the availability for.'))
            to_assign_moves.action_assign()
        return True

    @api.multi
    def rereserve_pick(self):
        """
        This can be used to provide a button that rereserves taking into account the existing pack operations
        Overridden here to limit the number of moves to rereserve
        """
        for pick in self:
            self.rereserve_quants(pick, move_ids = [m.id for m in pick.move_lines if m.reserved_quant_ids])

