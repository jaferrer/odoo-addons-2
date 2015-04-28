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


import openerp.addons.decimal_precision as dp
from datetime import timedelta, date
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp import fields, models, api, _

class stock_warehouse (models.Model):
    _inherit = "stock.warehouse.orderpoint"
    fill_strategy = fields.Selection([('max',"Maximal quantity"),('duration','Foresight duration')],
                                     string="Procurement strategy", help="Alert choice for a new procurement order",
                                     default="max")
    fill_duration = fields.Integer(string="Foresight duration", help="Number of days" )
    product_max_qty_operator = fields.Float(string='Maximum Quantity',
            digits_compute=dp.get_precision('Product Unit of Measure'),
            help="When the virtual stock goes below the Min Quantity, Odoo generates "\
            "a procurement to bring the forecasted quantity to the Quantity specified as Max Quantity.")
    product_max_qty = fields.Float(compute='_get_max_qty', inverse="_set_max_quantity")

    @api.one
    @api.depends('product_max_qty_operator', 'fill_strategy', 'fill_duration')
    def _get_max_qty(self):
        if self.fill_strategy == 'max':
            self.product_max_qty = self.product_max_qty_operator
        else:
            date_today = date.today()
            time_delta = timedelta(self.fill_duration)
            search_end_date = date.strptime(date_today + time_delta, DEFAULT_SERVER_DATE_FORMAT)
            moves = self.env['stock.move'].search([('product_id', '=', self.product_id.id),
                                                   ('location_id', '=', self.location_id.id),
                                                   ('state', 'in', ['confirmed', 'waiting']),
                                                   ('date','<=',search_end_date)])
            self.product_max_qty = sum([m.product_qty for m in moves])

    @api.one
    def _set_max_quantity(self):
        self.product_max_qty_operator = self.product_max_qty

