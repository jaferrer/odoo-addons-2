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

from openerp import models, fields, api, exceptions


class SplitLine(models.TransientModel):
    _name = 'split.line'
    _description = "Split Line"

    def _get_pol(self):
        return self.env['purchase.order.line'].browse(self.env.context.get('active_id'))

    line_id = fields.Many2one('purchase.order.line', string="Direct parent line in purchase order", default=_get_pol,
                              required=True, readonly=True)
    qty = fields.Float(string="New quantity of direct parent line")

    @api.multi
    def _check_split_possible(self):

        """
        Raises error if it is impossible to split the purchase order line.
        """

        self.ensure_one()
        if self.env.context.get('active_ids') and len(self.env.context.get('active_ids')) > 1:
            raise exceptions.except_orm(_('Error!'), _("Please split lines one by one"))
        else:
            if self.qty <= 0:
                raise exceptions.except_orm(_('Error!'), _("Impossible to split a negative or null quantity"))
            if self.line_id.state not in ['draft', 'confirmed']:
                raise exceptions.except_orm(_('Error!'), _("Impossible to split line which is not in state draft or "
                                                           "confirmed"))
            if self.line_id.state == 'draft':
                if self.qty >= self.line_id.product_qty:
                    raise exceptions.except_orm(_('Error!'), _("Please choose a lower quantity to split"))
        if self.line_id.state == 'confirmed':
            _sum = sum(x.product_uom_qty for x in self.line_id.move_ids if x.state == 'done')
            if self.qty < _sum:
                raise exceptions.except_orm(_('Error!'), _("Impossible to split a move in state done"))
            if self.qty >= sum([m.product_uom_qty for m in self.line_id.move_ids if m.state != 'cancel']):
                raise exceptions.except_orm(_('Error!'), _("Please choose a lower quantity to split"))

    @api.multi
    def do_split(self):

        """
        Separates a purchase order line into two ones.
        """

        self._check_split_possible()

        # Reduce quantity of original move
        original_qty = self.line_id.product_qty
        new_pol_qty = original_qty - self.qty
        self.line_id.with_context(no_update_moves=True).write({'product_qty': self.qty})

        # Get a line_no for the new purchase.order.line
        father_line_id = self.line_id.father_line_id or self.line_id
        orig_line_no = father_line_id.line_no or "0"
        new_line_no = orig_line_no + ' - ' + str(father_line_id.children_number + 1)

        # Create new purchase.order.line
        new_pol = self.line_id.with_context(no_update_moves=True).copy({
            'product_qty': new_pol_qty,
            'move_ids': False,
            'children_line_ids': False,
            'line_no': new_line_no,
            'father_line_id': father_line_id.id,
        })

        # Dispatch moves if the original purchase.order.line was confirmed
        if self.line_id.state == 'confirmed':
            moves = self.line_id.move_ids.filtered(lambda m: m.state not in ['draft', 'done', 'cancel']) \
                .sorted(key=lambda m: m.product_qty)
            moves_to_keep = self.env['stock.move']
            move_to_split = self.env['stock.move']

            # Define what to do with each move
            _sum = sum(x.product_uom_qty for x in self.line_id.move_ids if x.state == 'done')
            if _sum != self.qty:
                for move in moves:
                    _sum += move.product_uom_qty
                    if _sum > self.qty:
                        move_to_split = move
                        break
                    if _sum == self.qty:
                        moves_to_keep += move
                        break
                    else:
                        moves_to_keep += move

            # Attach relevant moves to new purchase.order.line
            moves_to_attach = moves - moves_to_keep - move_to_split
            moves_to_attach.write({'purchase_line_id': new_pol.id})
            # Split the move to split if any
            if move_to_split:
                self.env['stock.move'].split(move_to_split, self.qty - sum([m.product_uom_qty for m in moves_to_keep]))
                move_to_split.purchase_line_id = new_pol
            # Try to assign all moves
            moves.action_assign()
            # Set the status of all lines
            self.line_id.order_id.set_order_line_status(self.line_id.state)