# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    price_cost = fields.Float("Prix de revient", readonly=True)

    @api.multi
    def _use_standard_price(self):
        self.ensure_one()
        return len(self.bom_ids) == 0

    @api.multi
    def _get_price(self):
        self.ensure_one()
        return self.standard_price

    @api.multi
    def search_price_cost_for_product(self):
        self.ensure_one()
        if self._use_standard_price():
            return self._get_price()
        else:
            price_cost = 0.0
            for rec in self.bom_ids[:1].bom_line_ids:
                bom_qty = rec.product_uom_id._compute_quantity(rec.product_qty, self.uom_id)
                price_cost += rec.product_id.search_price_cost_for_product() * bom_qty
            return price_cost

    @api.multi
    def cron_update_price_cost(self):
        products = self.env['product.product'].search([])
        for rec in products:
            cost = rec.search_price_cost_for_product()
            rec.update({'price_cost': cost})
