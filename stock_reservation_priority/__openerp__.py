# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
    'name': 'Stock Reservation Priority',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    "summary": "",
    "category": "Warehouse Management",
    "depends": [
        "stock",
    ],
    'description': """
Stock Reservation Priority
===================================
This module introduces priority in (re)reservation of quants for pickings. A move with no quant reserved will always
have priority over another one if it has higher priority or same priority and earlier date. This is still true if the
less prioritary move has to be unassigned.
""",
    "website": "http://www.ndp-systemes.fr",
    "contributors": [],
    "data": [],
    "demo": ['tests/test_stock_reservation_priority.xml'],
    "installable": True,
}
