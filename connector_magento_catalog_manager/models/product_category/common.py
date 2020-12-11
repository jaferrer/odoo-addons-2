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


class MagentoProductCategoryAdapter(Component):
    _inherit = 'magento.product.category.adapter'

    @staticmethod
    def _normalize_data(data):
        return {'category': data}

    def create(self, data):
        """ Create a record on the external system """
        if self.collection.version == '1.7':
            return super(MagentoProductCategoryAdapter, self).create(data)
        return super(MagentoProductCategoryAdapter, self).create(self._normalize_data(data))

    def write(self, external_id, data, storeview_id=None):
        """ Update records on the external system """
        if self.collection.version == '1.7':
            return super(MagentoProductCategoryAdapter, self).write(external_id, data)
        return super(MagentoProductCategoryAdapter, self).write(external_id, self._normalize_data(data))


class MagentoProductCategoryListener(Component):
    _name = 'magento.product.category.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['magento.product.category', 'product.category']

    @staticmethod
    def export(record):
        bindings = record
        if record._name == 'product.category':
            bindings = record.magento_bind_ids

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
