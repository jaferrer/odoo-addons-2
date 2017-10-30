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
    'name': 'Update manufacturing orders',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Product',
    'depends': ['mrp'],
    'description': """
Update manufacturing orders
===========================
This module allows to change manually the list of scheduled products, and to generate the necessary stock moves to match the scheduled needs for this manufacturing order.
It also allows to update a manufacturing order after a modification of the BOM used. In this case, it does not take account of the possible changes in the list of scheduled products before the update.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
             'manufacturing_order_update.xml'],
    'demo': [
        'test_manufacturing_order_update.xml'
    ],
    'test': [],
    'installable': False,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}