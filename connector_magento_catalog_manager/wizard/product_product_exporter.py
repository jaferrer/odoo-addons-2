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
from odoo import models, fields, api


class ProductProductExporter(models.TransientModel):
    _name = 'product.product.exporter.wizard'

    product_tmpl_id = fields.Many2one('product.template', u"Article")
    product_id = fields.Many2one('product.product', u"Article", required=True)
    backend_id = fields.Many2one('magento.backend', u"Backend", required=True)

    @api.model
    def default_get(self, fields_list):
        res = super(ProductProductExporter, self).default_get(fields_list)
        res.setdefault('backend_id', self.env['magento.backend'].search([], limit=1).id)
        if self.env.context.get('active_model') == 'product.product':
            res.setdefault('product_id', self.env.context.get('active_id'))
        elif self.env.context.get('active_model') == 'product.template':
            product_tmpl_id = self.env.context.get('active_id')
            res.setdefault('product_tmpl_id', product_tmpl_id)
            res.setdefault('product_id', self.env['product.product'].search([
                ('product_tmpl_id', '=', product_tmpl_id)
            ], limit=1).id)

        return res

    @api.multi
    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        self.ensure_one()
        if self.product_tmpl_id:
            self.product_id = self.product_tmpl_id.product_variant_id

    @api.multi
    def apply(self):
        self.env['magento.product.product'].get_or_create_bindings(self.product_id, self.backend_id)
        # TODO trigger listener or manually trigger export
