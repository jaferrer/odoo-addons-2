# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
import os

from odoo import api, models, fields


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    point_of_break = fields.Date(u"Point Of Break Date", compute='_compute_point_of_break')

    @api.multi
    def _compute_point_of_break(self):
        for rec in self:
            rec.point_of_break = self.env['stock.quantity'].search([
                ('product_id', '=', rec.product_id.id),
                ('location_id', '=', rec.location_id.id),
                ('company_id', '=', rec.company_id.id),
                ('stock_qty', '<', rec.product_min_qty)
            ], order="date_stock_change asc", limit=1).date_stock_change or False

    @api.multi
    def action_view_graph_move(self):
        action = self.env.ref('stock_out_of_stock.action_stock_quantity').read()[0]
        action['domain'] = [
            ('product_id', '=', self.product_id.id),
            ('location_id', '=', self.location_id.id),
            ('company_id', '=', self.company_id.id),
        ]
        action['context'] = {
            'graph_measure': 'stock_qty'
        }
        return action