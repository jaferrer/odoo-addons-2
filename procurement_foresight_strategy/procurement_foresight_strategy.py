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

from datetime import datetime

import openerp.addons.decimal_precision as dp
from openerp import fields, models, api


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    fill_strategy = fields.Selection([('max', "Maximal quantity"), ('duration', 'Foresight duration')],
                                     string="Procurement strategy", help="Alert choice for a new procurement order",
                                     default="max")
    fill_duration = fields.Integer(string="Foresight duration", help="Number of days")
    product_max_qty_operator = fields.Float(
        string='Maximum Quantity',
        digits_compute=dp.get_precision('Product Unit of Measure'),
        help="When the virtual stock goes below the Min Quantity, Odoo generates "
        "a procurement to bring the forecasted quantity to the Quantity specified as Max Quantity.")
    product_max_qty = fields.Float(compute='_compute_product_max_qty', inverse="_set_max_quantity")

    @api.one
    @api.depends('product_max_qty_operator', 'fill_strategy', 'fill_duration')
    def _compute_product_max_qty(self):
        self.product_max_qty = self.get_max_qty(datetime.now())

    @api.one
    def _set_max_quantity(self):
        self.product_max_qty_operator = self.product_max_qty

    @api.multi
    def get_max_qty(self, date):
        """Returns the orderpoint maximum quantity for the given date.

        :param date: datetime at which we want to calculate the maximum quantity
        """
        self.ensure_one()
        if self.fill_strategy == 'max':
            return self.product_max_qty_operator
        else:
            if not date:
                return 0
            search_end_date = self.location_id.schedule_working_days(self.fill_duration + 1, date)
            moves = self.env['stock.move'].search([('product_id', '=', self.product_id.id),
                                                   ('location_id', '=', self.location_id.id),
                                                   ('state', 'in', ['confirmed', 'waiting']),
                                                   ('date', '<=', fields.Datetime.to_string(search_end_date)),
                                                   ('date', '>', fields.Datetime.to_string(date))])
            return sum([m.product_qty for m in moves])
