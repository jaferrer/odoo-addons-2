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
import logging

from odoo.addons.component.core import AbstractComponent
from odoo.addons.connector_magento_catalog_manager.components.exceptions import BadConnectorAnswerException


_logger = logging.getLogger(__name__)


class MagentoAdapter(AbstractComponent):
    _inherit = 'magento.adapter'

    def _call(self, url, data=None, http_method=None, **kwargs):
        _logger.info(u"MAGENTO %s %s REQUESTED %s", http_method, url, data)
        res = super(MagentoAdapter, self)._call(url, data, http_method=http_method, **kwargs)
        _logger.info(u"MAGENTO %s %s ANSWERED %s", http_method, url, str(res)[:2048])
        return res

    def create(self, data):
        """ Create a record on the external system """
        if self.collection.version == '1.7':
            return super(MagentoAdapter, self).create(data)
        ans = self._call(self._magento2_model, data, http_method='POST')
        if not ans.get(self._magento2_key):
            raise BadConnectorAnswerException(self._magento2_model, 'POST', ans)
        return ans[self._magento2_key]

    def write(self, external_id, data):
        """ Update records on the external system """
        if self.collection.version == '1.7':
            return super(MagentoAdapter, self).write(external_id, data)
        url = "%s/%s" % (self._magento2_model, self.escape(external_id))
        ans = self._call(url, data, http_method='PUT')
        if not ans.get(self._magento2_key):
            raise BadConnectorAnswerException(url, 'PUT', ans)
        return ans[self._magento2_key]

    def delete(self, external_id):
        """ Delete a record on the external system """
        if self.collection.version == '1.7':
            return super(MagentoAdapter, self).delete(external_id)
        url = '%s/%s' % (self._magento2_model, self.escape(external_id))
        ans = self._call(url, None, http_method='DELETE')
        if ans is not True:
            raise BadConnectorAnswerException(url, 'DELETE', ans)
        return ans

    def read(self, external_id, attributes=None, storeview=None):
        """ Returns the information of a record """
        if self.collection.version == '1.7':
            return super(MagentoAdapter, self).read(external_id, attributes, storeview)
        if self._magento2_key:
            url = '%s/%s' % (self._magento2_model, self.escape(external_id))
            ans = self._call(url, None, http_method='GET', storeview=storeview)
        else:
            answers = self._call(self._magento2_model, None)
            ans = next(record for record in answers if record['id'] == external_id)
        return ans
