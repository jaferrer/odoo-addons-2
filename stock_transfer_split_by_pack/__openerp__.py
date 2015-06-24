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
    'name': 'Stock Transfer Split by Pack',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Warehouse',
    'depends': ['stock','web_action_target_popup'],
    'description': """
Stock Transfer Split by Pack
============================
This module will add a "Split in Pack" button in the stock transfer view next to the native "Split" button. This button
will open a pop-up window asking for a quantity and if we should create packs. The amount of the line will then be split
in multiple lines of the selected quantity and a pack will be created for these lines if the options was selected. The
remaining quantity, if any, will stay in the original line.

This module is largely inspired from Akretion & Odoo Community Association (OCA) stock_transfer_split_multi module.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'views/stock_transfer_split_by_pack.xml',
        'views/stock_transfer_details.xml',
    ],
    'demo': [
        'stock_transfer_split_by_pack_demo.xml',
    ],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
