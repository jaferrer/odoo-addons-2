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

from odoo.addons.component.core import AbstractComponent


class MagentoAdapter(AbstractComponent):
    _inherit = 'magento.adapter'

    def create(self, data):
        """ Create a record on the external system """
        if self.collection.version == '1.7':
            return super(MagentoAdapter, self).create(data)
        return self._call(self._magento2_model, data, http_method='POST')

    def write(self, external_id, data):
        """ Update records on the external system """
        if self.collection.version == '1.7':
            return super(MagentoAdapter, self).write(external_id, data)
        url = "%s/%s" % (self._magento2_model, self._magento2_key or 'id')
        raise self._call(url, data, http_method='PUT')

    def delete(self, external_id):
        """ Delete a record on the external system """
        if self.collection.version == '1.7':
            return super(MagentoAdapter, self).delete(external_id)
        url = "%s/%s" % (self._magento2_model, self._magento2_key or 'id')
        raise self._call(url, http_method='DELETE')
