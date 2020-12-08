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
from odoo.addons.component.core import Component


class ProductProductAdapter(Component):
    _inherit = 'magento.product.product.adapter'

    def _root_magento_fields(self):
        """Returns the fields at the root of the JSON of magento product data"""
        return ["id", "sku", "name", "attribute_set_id", "price", "status", "visibility", "type_id", "created_at",
                "updated_at", "weight", "extension_attributes", "product_links", "options", "media_gallery_entries",
                "tier_prices"]

    def _normalize_data(self, record):
        """Returns a dict with all keys which are not magento root fields moved into the 'custom_attributes' key"""
        res = {
            'custom_attributes': []
        }
        for key, value in record.iteritems():
            if key == 'custom_attributes':
                continue
            if key in self._root_magento_fields():
                res[key] = value
                continue
            res['custom_attributes'].append({
                'attribute_code': key,
                'value': value,
            })
        return {'product': res}

    def create(self, data):
        """ Create a record on the external system """
        if self.collection.version == '1.7':
            return super(ProductProductAdapter, self).create(data)
        return super(ProductProductAdapter, self).create(self._normalize_data(data))

    def write(self, external_id, data, storeview_id=None):
        """ Update records on the external system """
        if self.collection.version == '1.7':
            return super(ProductProductAdapter, self).write(external_id, data, storeview_id)
        # return super(ProductProductAdapter, self).write(external_id, self._normalize_data(data))
        # Because of some nonsense in the connector_magento module, we are forced to make a dirty bypass of the parent
        # model here to avoid a NonImplementedError (despite the write being impleted in a parent model)
        from ...components.backend_adapter import MagentoAdapter
        return MagentoAdapter.write(self, external_id, self._normalize_data(data))


class MagentoProductProductListener(Component):
    _name = 'magento.product.product.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['magento.product.product', 'product.product', 'product.template']

    @staticmethod
    def export(record):
        bindings = record
        if record._name == 'product.product':
            bindings = record.magento_bind_ids
        elif record._name == 'product.template':
            bindings = record.mapped('product_variant_ids.magento_bind_ids')

        for binding in bindings:
            binding.with_delay().export_record()

    def on_record_create(self, record, fields=None):
        if record.env.context.get('connector_no_export'):
            return
        self.export(record)

    def on_record_write(self, record, fields=None):
        if record.env.context.get('connector_no_export'):
            return
        self.export(record)


class MagentoProductProductDeleter(Component):
    _inherit = 'magento.exporter.deleter'
    _name = 'magento.product.product.deleter'
    _apply_on = ['product.product']
