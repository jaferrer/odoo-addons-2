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
    'name': 'Sale Expedition By Order Line',
    'sequence': 1,
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Sale',
    'depends': [
        'sale_line_numbers', 'stock_performance_improved', 'stock_transfert_picking_type', 'sale_date_planned',
        'connector', 'sale_backlog', 'sale_order_workflow_improved'
    ],
    'description': """
Sale Expedition By Order Line
=============================
This module improves the initial expedition process. It allows to make it sale order line by sale order line.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': ['wizard.xml',
             'sale_expedition_by_order_line.xml',
             'cron.xml',
             ],
    'demo': ['tests/test_sale_expedition_by_order_line.xml'],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
