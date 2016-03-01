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
        # Transfer all pickings which have an auto move assigned
        moves = self.filtered(lambda m: m.state == 'assigned' and m.auto_move)
        picking_ids = {m.picking_id.id for m in moves}
        todo_pickings = self.env['stock.picking'].browse(picking_ids)
        # We create packing operations to keep packing if any
        pickings_to_prepare_partial = self.env['stock.picking']
        for picking in todo_pickings:
            moves_to_change_of_picking = picking.move_lines.filtered(lambda move: move in moves)
            # We change the moves of picking only if the move_lines of the current picking contain mixed moves from
            # list 'moves' and other ones
            if moves_to_change_of_picking and moves_to_change_of_picking != picking.move_lines:
                new_picking = picking.copy({'move_lines': [], 'pack_operation_ids': []})
                moves_to_change_of_picking.write({'picking_id': new_picking.id})
                # We call 'do_prepare_partial' on pickings with packops which lost moves in action.
                if picking.pack_operation_ids:
                    pickings_to_prepare_partial |= picking
                pickings_to_prepare_partial |= new_picking
            else:
                pickings_to_prepare_partial |= picking
        pickings_to_prepare_partial.do_prepare_partial()
        moves.action_done()


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


class stock_auto_move_location_path(models.Model):
    _inherit = 'stock.location.path'

    @api.model
    def _prepare_push_apply(self, rule, move):
        """Set auto move to the new move created by push rule."""
        res = super(stock_auto_move_location_path, self)._prepare_push_apply(rule, move)
        res.update({
            'auto_move': (rule.auto == 'auto'),
        })
        return res
