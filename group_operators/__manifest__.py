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
    'name': 'Extra Group Operators',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Technical Settings',
    'depends': ['base'],
    'description': """
Extra Group Operators
=====================
This module implements new aggregate functions in PostgreSQL to be used in group_operator parameter of fields.

Currently implements:

- median: This operator will return the median of a list. This function may prove particularly useful when dealing with
  cumulative fields inside the database, particularly in DB views.
- pos_avg: This operator calculates the average of values in a list that are greater or equal to 0, ignoring any
  negatives one. It may prove useful when we need to exclude some lines from our average.

Note:

This module removes and adds again the aggregate function in the database, so make sure that all modules using these new
aggregate functions depend from this module so that they get updated.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
