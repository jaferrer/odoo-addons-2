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
    'name': 'Asynchronous Scheduler for Stock',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Procurement',
    'depends': ['stock','scheduler_async'],
    'description': """
Asynchronous Scheduler for Stock
================================
Asynchronous Scheduler reimplements the procurement scheduler using the 'OCA/connector' framework to be able to monitor
the scheduler running in the background.

This module brings the implementation of the scheduler part linked with the stock module.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': True,
    'license': 'AGPL-3',
    'application': False,
}
