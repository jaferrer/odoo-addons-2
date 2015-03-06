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
    'name': 'Stock Procurement Just-In-Time',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Warehouse',
    'depends': ['stock','group_operators'],
    'description': """
Stock Procurement Just-In-Time
==============================
Just-In-Time (JIT) is an inventory strategy companies employ to increase efficiency and decrease waste by receiving
goods only as they are needed in the production process, thereby reducing inventory costs.

This modules implements a new calculation method for minimum stock rules that creates procurements for products just
before they are needed instead of creating them at earliest.

This calculation is done for each minimum stock rule, in the stock location defined by the rule. The needs are defined
by the outgoing stock moves in "Waiting availability" or "Available" statuses. This implies that the outgoing moves are
confirmed beforehand, either by already confirmed manufacturing orders, by already confirmed sale orders or by a sales
forecast module that creates confirmed moves to represent future sales.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'security/ir.model.access.csv',
        'stock_procurement_jit_view.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
