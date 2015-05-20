# -*- coding: utf8 -*-
#
# Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api, _

class mrp_production(models.Model):
    _inherit = "mrp.production"
    product_lines = fields.One2many(readonly=False)

    @api.one
    def update_moves(self):
        useless_moves = []
        changes_to_do = []
        list_products_to_change = []
        needed_new_moves = []
        for item in self.move_lines:
            if not item.product_id in [x.product_id for x in self.product_lines]:
                useless_moves += [item]
        for move in useless_moves:
            move.with_context({'cancel_procurement': True}).action_cancel()
        for item in self.move_lines:
            total_old_need = 0
            for x in self.move_lines:
                if x.product_id == item.product_id:
                    total_old_need += x.product_uom_qty
            total_new_need = sum([x.product_qty for x in self.product_lines if x.product_id == item.product_id])
            if not item.product_id in list_products_to_change and total_new_need != total_old_need and total_new_need != 0:
                changes_to_do += [[item.product_id, total_new_need - total_old_need, total_new_need, total_old_need]]
                list_products_to_change += [item.product_id]
        for change in changes_to_do:
            product = change[0]
            qty = change[1]
            if qty > 0:
                move = self._make_consume_line_from_data(self, product, product.uom_id.id, qty, False, 0)
                self.env['stock.move'].browse(move).action_confirm()
            else:
                _sum = sum([x.product_qty for x in self.move_lines if x.product_id == product])
                while _sum > change[2]:
                    for item in self.move_lines:
                        list_1 = [x.product_qty for x in self.move_lines if x.product_id == product and x.state != 'cancel']
                        maximum = 0
                        if len(list_1) != 0:
                            maximum = max(list_1)
                        if item.product_id == product and item.product_qty == maximum and item.state != 'cancel':
                            _sum -= item.product_qty
                            item.with_context({'cancel_procurement': True}).action_cancel()
                            break
                if _sum < change[2]:
                    product = change[0]
                    move = self._make_consume_line_from_data(self, product, product.uom_id.id, change[2] - _sum, False, 0)
                    self.env['stock.move'].browse(move).action_confirm()

        for item in self.product_lines:
            if item.product_id not in [y.product_id for y in self.move_lines if y.state != 'cancel']:
                needed_new_moves += [item]

        for item in needed_new_moves:
            product = item.product_id
            move = self._make_consume_line_from_data(self, product, product.uom_id.id, item['product_qty'], False, 0)
            self.env['stock.move'].browse(move).action_confirm()

    @api.multi
    def write(self, vals):
        result = super(mrp_production, self).write(vals)
        for object in self:
            if object.move_lines:
                object.update_moves()
        return result

    @api.multi
    def button_update(self):
        self.ensure_one()
        self._action_compute_lines()
        self.update_moves()