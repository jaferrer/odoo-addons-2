# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
    'name': 'Android NDP TCB',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Technical Settings',
    'depends': [
        'stock',
        'stock_picking_batch',
    ],
    'description': """
NDP Terminal code barre
=======================
Modules pour la synchro entre android et Odoo
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': ['views/push_tcb_view.xml',
             'views/push_tcb_menu.xml',
             'views/stock_picking_operation.xml',
             # 'views/stock.xml',
             'views/stock_picking.xml',
             'security/ir.model.access.csv',
             ],
    'demo': [
        # 'tests/test_tcb_synchro.xml',
    ],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
