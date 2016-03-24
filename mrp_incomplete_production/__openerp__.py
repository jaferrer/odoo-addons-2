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
    'name': 'Partial Productions',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Product',
    'depends': ['mrp_manufacturing_order_update', 'stock_quant_packages_moving_wizard'],
    'description': """
Partial Productions
===================
This module allows to mark as done a manufacturing order (MO) even if all the products needed are not available.
If none are available, it returns an error message.
If all the products are available, it does not change anything.
If the products are partially available, it marks the MO as done, and consumes only the available products.
It also creates another MO, with the products needed but not available at the conclusion of the first MO.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'views/mrp.xml',
        'views/stock.xml',
        'data/mrp_incomplete_production_workflow.xml'
    ],
    'demo': [
        'data/test_mrp_incomplete_production.xml'
    ],
    'test': [],
    'installable': False,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}