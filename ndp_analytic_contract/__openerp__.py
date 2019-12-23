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
    'name': 'NDP analytic contract',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Contract',
    'depends': [
        'sale',
        'account',
        'connector',
    ],
    'description': """
NDP analytic contract
=====================
This module creates the notion of contract regrouping several sale orders and 3 types of order lines : classic sale
order lines, sale recurrence lines and sale consumption lines.

""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'data/data.xml',
        'views/data.xml',
        'views/analytic_contract.xml',
        'views/sale_recurrence_line.xml',
        'views/sale_consu_line.xml',
        'views/sale_consu_group.xml',
        'views/contract_billing_wizard.xml',
        'views/consu_type.xml',
        'views/cron.xml',
    ],
    'demo': ['tests/test_data.xml'],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
