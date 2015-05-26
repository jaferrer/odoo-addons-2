# -*- coding: utf8 -*-
#
# Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
    'name': 'Partial productions',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Product',
    'depends': ['mrp','product', 'stock'],
    'description': """
Partial productions
===================
This module allows to mark as done a manufactoring order (MO) even if all the products needed are not available.
If no one is available, it returns an error message.
If all the products are available, it does not change anything.
If the products are partially available, it marks the MO as done, and consumes only the available products.
It also creates another MO, with the products needed but not available at the conclusion of the first MO.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
             'mrp_incomplete_production.xml'
    ],
    'demo': [
        'test_mrp_incomplete_production.xml'
    ],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}