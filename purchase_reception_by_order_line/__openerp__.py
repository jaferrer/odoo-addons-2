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
    'name': 'Purchase Reception By Order Line',
    'sequence': 1,
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Purchase',
    'depends': ['purchase_line_numbers', 'stock_performance_improved'],
    'description': """
Purchase Reception By Order Line
================================
This module improves the initial reception process. It allows to make it purchase order line by purchase order line.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': ['purchase_reception_by_order_line.xml',
             'wizard.xml'],
    'demo': ['tests/test_purchase_reception_by_order_line.xml'],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
