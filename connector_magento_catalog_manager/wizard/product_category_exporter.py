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


class ProductCategoryExporter(models.TransientModel):
    _name = 'product.category.exporter.wizard'

    categ_id = fields.Many2one('product.category', u"Catégorie", required=True)
    backend_id = fields.Many2one('magento.backend', u"Backend", required=True)

    @api.model
    def default_get(self, fields_list):
        res = super(ProductCategoryExporter, self).default_get(fields_list)
        res.setdefault('backend_id', self.env['magento.backend'].search([], limit=1).id)
        if self.env.context.get('active_model') == 'product.category':
            res.setdefault('categ_id', self.env.context.get('active_id'))

        return res

    @api.multi
    def apply(self):
        self.env['magento.product.category'].get_or_create_bindings(self.categ_id, self.backend_id)
        # TODO trigger listener or manually trigger export
