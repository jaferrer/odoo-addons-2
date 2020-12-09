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
from odoo.addons.connector.exception import MappingError


class ProductCategoryExporter(Component):
    _name = 'magento.product.category.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.category']

    def _export_dependencies(self):
        super(ProductCategoryExporter, self)._export_dependencies()
        if self.binding.parent_id:
            parent_binding = self.env['magento.product.category'].get_or_create_bindings(
                self.binding.parent_id, self.backend_record)
            if not self.binding.magento_parent_id:
                parent_binding.export_record()
                self.binding.magento_parent_id = parent_binding.id


class ProductCategoryExportMapper(Component):
    _name = 'magento.product.category.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.product.category']

    direct = [
        ('name', 'name')
    ]

    @mapping
    def description(self, record):
        if record.description:
            return {'description': record.description}

    @mapping
    def is_active(self, record):
        return {'is_active': int(record.active)}

    @mapping
    def level(self, record):
        level = 0
        while record.parent_id:
            level += 1
            record = record.parent_id
        return {'level': level}

    @mapping
    def parent_id(self, record):
        if record.parent_id:
            if not record.magento_parent_id:
                raise MappingError("The product category %s has a parent %s which has not been exported yet" %
                                   (record.display_name, record.parent_id.display_name))
            return {'parent_id': record.magento_parent_id.external_id}
