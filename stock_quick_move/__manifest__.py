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
    'name': 'Stock Quick Move',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'stock',
    'depends': ['stock'],
    'description': """
Stock Quick Move
================
This module provides a wizard to create a stock picking from a few information.
It is intended to be used in custom actions.

The wizard follows this logic:
- Select a location
- Select a product, filtered on products of the quants in location
- Select a lot, filtered on lots of the quants of this product in location
- Select a qty, which must be lower or equal to the available quantity
- Select a picking type
- Choose whether to create and validate picking or only create
- Validate
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'wizard/stock_quick_move_wizard.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
