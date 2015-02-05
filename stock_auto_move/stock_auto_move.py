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

from openerp import fields, models, api

class stock_auto_move_move(models.Model):
    _inherit = "stock.move"

    auto_move = fields.Boolean("Automatic move", help="If this option is selected, the move will be automatically "
                                                      "processed as soon as the products are available.")

    @api.multi
    def action_assign(self):
        super(stock_auto_move_move, self).action_assign()
        for move in self:
            if move.state == 'assigned' and move.auto_move:
                if not move.linked_move_operation_ids and move.picking_id:
                    # To get packages transferred at once if quants are in package
                    move.picking_id.do_prepare_partial()
                move.action_done()


class stock_auto_move_procurement_rule(models.Model):
    _inherit = 'procurement.rule'

    auto_move = fields.Boolean("Automatic move", help="If this option is selected, the generated move will be "
                                                      "automatically processed as soon as the products are available. "
                                                      "This can be useful for situations with chained moves where we "
                                                      "do not want an operator action.")


class stock_auto_move_procurement(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _run_move_create(self, procurement):
        res = super(stock_auto_move_procurement, self)._run_move_create(procurement)
        res.update({'auto_move': procurement.rule_id.auto_move})
        return res

