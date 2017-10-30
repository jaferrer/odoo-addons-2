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
    'name': 'Hide Picking Types in Stock Operations',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Warehouse',
    'depends': ['stock'],
    'description': """
Hide Picking Types in Stock Operations
======================================
This module adds a field that allow to hide a picking type in all operations menu of the warehouse.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'stock_picking_type_hide_view.xml'
    ],
    'demo': [],
    'test': [],
    'installable': False,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
