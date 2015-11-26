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
from datetime import datetime


class QuantOriginStockQuant(models.Model):
    _inherit = 'stock.quant'

    origin = fields.Char(string='Quant origin', compute='_compute_origin')

    @api.multi
    def _compute_origin(self):

        query = """
            select quant_id,origin from (
                select tmp.quant_id,tmp.origin,tmp.order_num, min(tmp.order_num) OVER (PARTITION BY tmp.quant_id)  from 
                (
                    select stock_quant_move_rel.quant_id,stock_move.origin, row_number() OVER (order by stock_move.date asc) order_num 
                    from stock_quant_move_rel
                    inner join stock_move on stock_move.id=stock_quant_move_rel.move_id
                    where stock_quant_move_rel.quant_id in %s
                ) tmp
            ) t
            where min=order_num
            order by quant_id asc
        """

        params = (tuple(self.ids),)
        self.env.cr.execute(query, params)

        rows = self.env.cr.fetchall()
        affect = {}
        for row in rows:
            affect[row[0]] = row[1]

        for rec in self:
            rec.origin = affect.get(rec.id, False)
