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


class MagentoIrAttachmentExporter(Component):
    _name = 'magento.ir.attachment.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.ir.attachment']

    def _comodel_data(self):
        # Currently, only product.product need images soooooo...
        comodel_binding = self.env['magento.product.product']
        comodel_adapter = self.component(usage='backend.adapter', model_name=comodel_binding._name)
        comodel_binding_record = comodel_binding.search([
            ('odoo_id.product_tmpl_id', '=', self.binding.odoo_id.res_id),
            ('backend_id', '=', self.backend_record.id)
        ], limit=1)
        return comodel_adapter._magento2_model, comodel_binding_record.external_id

    def _create(self, data):
        self._validate_create_data(data)
        return self.backend_adapter.create(data, *self._comodel_data())

    def _update(self, data):
        assert self.external_id
        self._validate_update_data(data)
        self.backend_adapter.write(self.external_id, data, *self._comodel_data())


class MagentoIrAttachmentMapper(Component):
    _name = 'magento.ir.attachment.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.ir.attachment']

    direct = [
        ('datas_fname', 'label'),
        ('id', 'position'),
    ]

    @mapping
    def hardcoded_params(self, record):
        return {
            'media_type': 'image',
            'disabled': False,
        }

    @mapping
    def types(self, record):
        return {'types': [record.image_type]}

    @mapping
    def content(self, record):
        return {
            'content': {
                'base64_encoded_data': record.datas,
                'name': record.datas_fname,
                'type': record.mimetype,
            }
        }
