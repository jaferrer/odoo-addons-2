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
            res['custom_attributes'].update({
                'attribute_code': key,
                'value': value,
            })
        return res

    def create(self, data):
        """ Create a record on the external system """
        if self.collection.version == '1.7':
            return super(ProductProductAdapter, self).create(data)
        return super(ProductProductAdapter, self).create(self._normalize_data(data))

    def write(self, external_id, data, storeview_id=None):
        """ Update records on the external system """
        if self.collection.version == '1.7':
            return super(ProductProductAdapter, self).write(external_id, data, storeview_id)
        return super(ProductProductAdapter, self).write(external_id, self._normalize_data(data))
