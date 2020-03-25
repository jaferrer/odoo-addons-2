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
    'name': 'Improved of the native stock module',
    'version': '1.0',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Stock',
    'depends': ['stock'],
    'description': """
Improved of the native stock module
===================================
This module improved the native Odoo module to manage the stock

The goal of this module is to add @api.v7 and @api.v8 on native stock function
for easy to call in a new style way

When necessary this module completely rewrite function folling this goal:
- The rewrite function must accept the same type of paramter and return the same as well.
- The rewrite should explain why.
- The rewrite should be in new api if possible.
- The rewrite should split big function to allow other module to customise the behavior.

All the test of the native stock module should success.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [],
    'test': [
        # '../stock/test/inventory.yml',
        # '../stock/test/move.yml',
        # '../stock/test/procrule.yml',
        # '../stock/test/stock_users.yml',
        # '../stock/test/shipment.yml',
        # '../stock/test/packing.yml',
        # '../stock/test/packingneg.yml',
        # '../stock/test/wiseoperator.yml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
