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

{
    'name': 'Prestashop Connector v1.7',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Connector',
    'depends': [
        'connector_prestashop_catalog_manager',
    ],
    'description': """
Prestashop Connector v1.7
=========================
This modules extend the connector_prestashop module for version 1.7.

You must install the `odoo_webservice_api` Prestashop module if your Prestashop version is less than 1.7.8.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'views/product_view.xml',
        'views/product_features.xml',
        'views/prestashop_backend.xml'
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
