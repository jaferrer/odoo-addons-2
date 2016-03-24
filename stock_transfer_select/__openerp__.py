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
    'name': 'Stock Transfer Select',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Warehouse',
    'depends': ['stock','web_action_target_popup','web_action_top_button'],
    'description': """
Stock Transfer Select
=====================
This modules adds a pop-up in the stock transfer wizard of a stock picking to select the pack operations to process.
This particularly useful in situations where there are hundreds of available products in a picking but we want to
process only a few. In this case, it avoids to press on the trash bin icon of hundreds of lines.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'stock_transfer_select_data.xml',
        'stock_transfer_select_view.xml',
    ],
    'demo': [],
    'test': [],
    'installable': False,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
