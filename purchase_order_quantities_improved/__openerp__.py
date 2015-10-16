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
    'name': 'Improvement of purchase order quantities calculation',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Product',
    'depends': ['purchase'],
    'description': """
Improvement of purchase order quantities calculation
====================================================
This module calculates the order quantities of each purchase order line in an improved way.
It considers all the procurement orders related to a purchase order line, calculates the global need, and sets the purchase quantity to a value which is higher or equal to the minimum purchase order of this product, for the supplier considered.
Furthermore, it sets the purchase quantity to a multiple of the number of articles contained in the standard packaging.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
             'supplierinfo.xml'
    ],
    'demo': [
        'test_order_quantities_demo.xml'
    ],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
