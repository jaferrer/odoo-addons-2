# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
import base64

from openerp.addons.connector_prestashop.models.product_image.common import ProductImageAdapter
from openerp.addons.connector_prestashop.unit.backend_adapter import PrestaShopWebServiceImage

from ..backend import prestashop_1_7


@prestashop_1_7
class ProductImageAdapterExtension(ProductImageAdapter):
    _model_name = 'prestashop.product.image'

    def create(self, attributes=None):
        api = PrestaShopWebServiceImage(
            self.prestashop.api_url, self.prestashop.webservice_key)
        # TODO: odoo logic in the adapter? :-(
        url = '{}/{}'.format(self._prestashop_model, attributes['id_product'])
        res = api.add(url, files=[(
            'image',
            attributes['filename'].encode('utf-8'),
            base64.b64decode(attributes['content'])
        )])
        return res['prestashop']['image']['id']
