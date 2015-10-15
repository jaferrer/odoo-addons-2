# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
    'name': 'Product Use Cases in BoMs',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Manufacture',
    'depends': ['mrp'],
    'description': """
Product Use Cases in BoMs
=========================
This modules adds a tree view available on a product to find recursively all the use cases of the component product
inside BoMs.

For a given product, this view shows all BoMs in which this product appear as a component. If the product of the
parent BoM is itself a component of another BoM, it is also displayed as a tree view.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'mrp_bom_use_cases_view.xml'
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}

