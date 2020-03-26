# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    price_cost_avg = fields.Float("Average price cost", readonly=True)

    @api.multi
    def cron_update_price_cost_avg(self):
        products = self.env['product.template'].search([])
        for rec in products:
            if len(rec.product_variant_ids) > 0:
                cost_avg = sum(rec.product_variant_ids.mapped('price_cost')) / len(rec.product_variant_ids)
                rec.update({'price_cost_avg': cost_avg})
