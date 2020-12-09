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
from datetime import datetime

import odoo
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector_magento.components.backend_adapter import MAGENTO_DATETIME_FORMAT


class MagentoIrAttachmentExporter(Component):
    _name = 'magento.ir.attachment.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.ir.attachment']

    def _should_import(self):
        # assert self.binding
        # if not self.external_id:
        #     return False
        # sync = self.binding.sync_date
        # if not sync:
        #     return True
        # record = self.backend_adapter.read(self.external_id, *self._comodel_data(), attributes=['updated_at'])
        # if not record.get('updated_at'):
        #     # in rare case it can be empty, in doubt, import it
        #     return True
        # sync_date = odoo.fields.Datetime.from_string(sync)
        # magento_date = datetime.strptime(record['updated_at'], MAGENTO_DATETIME_FORMAT)
        # return sync_date < magento_date
        # It seems like we should never import an ir.attachment during the export process
        return False

    def _comodel_data(self):
        return self.binding.comodel_data()

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

    @mapping
    def position(self, record):
        return {'position': record.sequence or 0}
