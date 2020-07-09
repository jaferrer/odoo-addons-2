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

from openerp.addons.connector.unit.mapper import backend_to_m2o
from openerp.addons.connector.unit.mapper import mapping
from openerp.addons.connector_prestashop.models.res_partner.importer import \
    PartnerImportMapper, AddressImportMapper

from ..backend import prestashop_1_7


@prestashop_1_7
class PartnerImportMapperExtension(PartnerImportMapper):
    _model_name = 'prestashop.res.partner'

    direct = [
        ('date_add', 'date_add'),
        ('email', 'email'),
        ('newsletter', 'newsletter'),
        ('company', 'company'),
        ('active', 'active'),
        ('note', 'comment'),
        (backend_to_m2o('id_shop_group'), 'shop_group_id'),
        (backend_to_m2o('id_shop'), 'shop_id'),
        (backend_to_m2o('id_default_group'), 'default_category_id'),
    ]

    @mapping
    def date_upd(self, record):
        if record['date_upd'] in ['0000-00-00 00:00:00', '']:
            return {}
        return {'date_upd': record['date_upd']}


@prestashop_1_7
class AddressImportMapperExtension(AddressImportMapper):
    _model_name = 'prestashop.address'

    direct = [
        ('address1', 'street'),
        ('address2', 'street2'),
        ('city', 'city'),
        ('other', 'comment'),
        ('phone', 'phone'),
        ('phone_mobile', 'mobile'),
        ('postcode', 'zip'),
        ('date_add', 'date_add'),
        (backend_to_m2o('id_customer'), 'prestashop_partner_id'),
    ]

    @mapping
    def date_upd(self, record):
        if record['date_upd'] in ['0000-00-00 00:00:00', '']:
            return {}
        return {'date_upd': record['date_upd']}
