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

from openerp import fields, models, api


class QuantOriginStockQuant(models.Model):
    _inherit = 'stock.quant'

    origin = fields.Char(string='Quant origin', compute='_compute_origin')

    @api.multi
    def _compute_origin(self):

        query = """SELECT
  quant_id,
  origin
FROM (
  SELECT
    tmp.quant_id,
    tmp.origin,
    tmp.order_num,
    min(tmp.order_num)
    OVER (PARTITION BY tmp.quant_id)
  FROM
    (
      SELECT
        stock_quant_move_rel.quant_id,
        stock_move.origin,
        row_number()
        OVER
        (
          ORDER BY stock_move.date ASC, stock_move.id ASC) order_num
      FROM stock_quant_move_rel
        INNER JOIN stock_move ON stock_move.id = stock_quant_move_rel.move_id
      WHERE stock_quant_move_rel.quant_id IN %s
) tmp
) t
WHERE min=order_num
ORDER BY quant_id ASC
        """

        params = (tuple(self.ids),)
        self.env.cr.execute(query, params)

        rows = self.env.cr.fetchall()
        affect = {}
        for row in rows:
            affect[row[0]] = row[1]

        for rec in self:
            rec.origin = affect.get(rec.id, False)
