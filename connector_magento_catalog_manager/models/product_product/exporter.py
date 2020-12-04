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
        return{'attribute_set_id': 10}
