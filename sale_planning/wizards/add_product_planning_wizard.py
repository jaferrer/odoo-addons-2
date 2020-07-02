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

from odoo import fields, models, api


class AddProductPlanningWizard(models.TransientModel):
    _name = 'add.product.planning.wizard'
    _description = "Add Product Planning Wizard"

    def _get_domain_product(self):
        product_domain = self.env['product.product']._get_products_for_sale_forecast(False)
        ctx_period_id = self.env.context.get('default_period_id')
        product_ids = self.env['sale.planning'].search([('period_id', '=', ctx_period_id)]).mapped('product_id')
        product_domain.append(('id', 'not in', product_ids.ids))
        return product_domain

    period_id = fields.Many2one('period.planning', string="Sale planning")
    product_ids = fields.Many2many('product.product', string="Product", domain=_get_domain_product)

    @api.multi
    def add(self):
        self.period_id.merge_products(self.product_ids)
