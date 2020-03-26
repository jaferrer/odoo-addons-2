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

from datetime import date

from odoo import api, models, fields


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    point_of_break = fields.Date(u"Point Of Break Date")
    deprioritize_point_of_break = fields.Boolean(u"Deprioritize", default=False)

    @api.multi
    def update_point_of_break(self, point_of_break):
        self.write({'point_of_break': point_of_break})

    @api.model
    def cron_update_point_of_break(self):
        mrp_productions = self.search([])
        products = mrp_productions.mapped('product_id')
        for product in products:
            mrp_products = mrp_productions.filtered(lambda p: p.product_id == product)
            for mrp_product in mrp_products:
                date_of_break = date(2100, 12, 31)
                if not mrp_product.deprioritize_point_of_break:
                    orderpoint = product.orderpoint_ids \
                        and min(product.orderpoint_ids, key=lambda x: x.product_min_qty or False)
                    if orderpoint:
                        date_of_break = self.env['stock.quantity'].search([
                            ('product_id', '=', orderpoint.product_id.id),
                            ('location_id', '=', orderpoint.location_id.id),
                            ('company_id', '=', orderpoint.company_id.id),
                            ('stock_qty', '<', orderpoint.product_min_qty)
                        ], order="date_stock_change asc", limit=1).date_stock_change or False
                mrp_product.update_point_of_break(date_of_break)
