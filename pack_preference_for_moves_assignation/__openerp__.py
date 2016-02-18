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
    'name': 'Package preference for moves assignation',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Stock',
    'depends': ['stock'],
    'description': """
Package preference for moves assignation
========================================
This modules overwrites removal strategies FIFO and LIFO. Stock moves are now forced to reserve all the quants in the
package of the first quant reserved (youngest or oldest, according to the removal strategy of the location), even if
the native preference should be given to another one.

It also reserves the quants which are not in a package or not in a lot first, if the given order implies to choose
between one of them.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [],
    'demo': ['tests/tests_data.xml'],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
