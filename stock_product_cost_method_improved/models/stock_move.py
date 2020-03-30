# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def product_price_update_after_done(self):
        """ We want to update every moves, even internal ones"""
        self._store_average_cost_price()

    @api.multi
    def _store_average_cost_price(self):
        """ Store the average price on the move and product

        only called when the product's cost method is 'real'
        Inherited to implement a weighted cost average, instead of a cost based on this quant
        """
        moves_per_product = {}
        remaining_moves = self.env['stock.move']

        for rec in self:
            if rec.product_id.cost_method != 'real':
                remaining_moves |= rec
            else:
                moves_per_product[rec.product_id] = moves_per_product.get(rec.product_id, self.env['stock.move']) | rec

        for product, moves in moves_per_product.iteritems():
            quants = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('qty', '>', 0),
                ('cost', '>', 0),
                ('location_id.usage', '=', 'internal'),
            ])

            if quants:
                avg_valuation_price = sum(q.qty * q.cost for q in quants) / sum(q.qty for q in quants)
                product.sudo().write({
                    'standard_price': avg_valuation_price
                })
                moves.write({
                    'price_unit': avg_valuation_price
                })
            else:
                remaining_moves |= moves

        # Remove internal moves from "self" before calling super()
        remaining_external_moves = remaining_moves.filtered(lambda move: move.location_dest_id.usage != 'internal')
        return super(StockMove, remaining_external_moves)._store_average_cost_price()
