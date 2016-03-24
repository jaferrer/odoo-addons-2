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
    'name': 'Procurement foresight strategy',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Product',
    'depends': ['stock_working_days'],
    'description': """
Procurement Foresight Strategy
==============================
This modules gives two possibilities for procurement orders.
Max quantity strategy makes procurements orders according to a maximum quantity.
Foresight strategy calculates this maximum quantity according to the scheduled stock moves during the period given by the user
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
             'procurement_foresight_strategy.xml'],
    'demo': [
        'procurement_foresight_strategy_demo.xml',
    ],
    'test': [],
    'installable': False,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}