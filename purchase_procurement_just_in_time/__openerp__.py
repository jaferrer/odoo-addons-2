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
    'name': 'Purchase Just-In-Time Extension',
    'sequence': 1,
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Purchase',
    'depends': ['purchase', 'purchase_order_quantities_improved', 'purchase_planning_improved',
                'stock_procurement_just_in_time', 'purchase_line_numbers', 'purchase_working_days',
                'stock_moves_to_assigned_pickings',
                ],
    'description': """
Purchase Just-In-Time Extension
===============================
Just-In-Time (JIT) is an inventory strategy companies employ to increase efficiency and decrease waste by receiving
goods only as they are needed in the production process, thereby reducing inventory costs.

When JIT procurement is enabled through the stock_procurement_just_in_time module, draft POs are created by the
scheduler with its required date set just as needed. While this is good to reduce inventory to the minimum, it requires
purchasing officers to be particularly responsive to changes of schedule. This implies being able to contact suppliers
to modify scheduling of already placed orders and to register the new promised date.

This modules implements a supplier backlog which enable purchase officers to see all the purchase order lines at
once, whichever purchase order they come from. The supplier backlog provides the following operational messages on
purchase order lines:

- "LATE by n days": The order line planned date is behind the required date by n days. This message appears only when n
  is above a configurable preset value.
- "EARLY by n days": The order line planned date is ahead of the required date by n days. This message appears only when
  n is above a configurable preset value.
- "REDUCE QTY to n [UoM]": One of the procurement order which generated the purchase order line has been cancelled. The
  qty ordered in this line is to be reduced to the quantity given.

Notes
-----
- This module depends on purchase_planning_improved and as such on purchase_working_days, which means that all the
  scheduling is made based on working days.

""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_view.xml',
        'views/time_frame.xml',
        'views/purchase_procurement_jit.xml',
        'views/purchase.xml',
        'views/wizard.xml',
        'views/partner.xml',
        'data/cron.xml',
        'data/data_group_by_period.xml',
    ],
    'demo': [
        'tests/test_purchase_scheduler_demo.xml',
    ],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
    'sequence': 50,
}
