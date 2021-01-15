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

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class ProductProductExporter(Component):
    _name = 'magento.product.product.generic.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.product']

    def _has_to_skip(self):
        return not self.binding.is_available_on_profilesmarket

    def _export_dependencies(self):
        super(ProductProductExporter, self)._export_dependencies()
        for categ in self.binding.categ_ids:
            categ_binding = self.env['magento.product.category'].get_or_create_bindings(categ, self.backend_record)
            categ_binding.export_record()

    def _get_related_images(self):
        return self.env['ir.attachment'].search([
            ('res_model', '=', 'product.template'),
            ('res_id', '=', self.binding.odoo_id.product_tmpl_id.id),
            ('res_field', 'in', ['image', 'image_medium', 'image_small']),
        ])

    def _filter_images(self, images):
        already_followed = self.env['magento.ir.attachment'].search([
            ('odoo_id', 'in', images.ids),
            ('backend_id', '=', self.backend_record.id)
        ]).mapped('odoo_id')
        return images - already_followed

    def _export_images(self):
        """ Export the related images

        Because they need the product's SKU, they have to be exported after it

        WARNING: it MUST be done on the 'all' storeview in order to be used correctly
        """
        images = self._filter_images(self._get_related_images())
        if images:
            bindings = self.env['magento.ir.attachment'].get_or_create_bindings(
                images, self.backend_record,
                comodel_external_name=self.backend_adapter._magento2_model,
                comodel_external_id=self.binding.external_id
            )
            for binding in bindings:
                binding.export_record()

    def _after_export(self):
        self._export_images()


class ProductExportMapper(Component):
    _name = 'magento.product.product.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.product.product']

    direct = [
        ('name', 'name'),
        ('description', 'description'),
        ('standard_price', 'cost'),
        ('description_sale', 'short_description'),
        ('default_code', 'sku'),
        ('product_type', 'type_id'),
        ('created_at', 'created_at'),
        ('updated_at', 'updated_at'),
    ]

    @mapping
    def status(self, record):
        return {'status': 1 if record.active else 0}

    @mapping
    def type_id(self, record):
        if record.type == 'product':
            return {'type_id': 'simple'}
        # TODO Complicated because for one odoo value 'service', we have 3 magento values
        #  ('virtual', 'downloadable', 'giftcard')
        return {'type_id': 'virtual'}

    @mapping
    def price(self, record):
        return {'price': record.list_price or 0.0}

    @mapping
    def weight(self, record):
        return {'weight': record.weight or 0.0}

    @mapping
    def attribute_set(self, record):
        # TODO create model and stuff
        return {'attribute_set_id': 10}

    @mapping
    def categories(self, record):
        categs = []
        for categ in record.categ_ids:
            categ_id = self.binder_for('magento.product.category').to_external(categ, wrap=True)
            categs.append(categ_id)
        return {'category_ids': categs}
