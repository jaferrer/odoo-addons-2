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
    'name': 'Purchase Schedule on Working Days',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Purchase',
    'depends': ['purchase','stock_working_days'],
    'description': """
Purchase Schedule on Working Days
=================================
This modules enables scheduling of purchase order lead times on working days defined by resources and associated calendars.

Resources can be defined for suppliers. When defined, supplier lead time is calculated counting only the
working days of the supplier.

Notes:
------

- When no applicable calendar is found, the module's default calendar is used which sets working days from Monday to
  Friday. This default calendar can be changed by authorized users.

- Purchase security margin (po_lead) is calculated using our warehouse's resource and not the supplier resource. This
  is intended so that RFQ schedule dates always end up on our opening days.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'purchase_working_days_view.xml',
    ],
    'demo': [
        'purchase_working_days_demo.xml',
    ],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
