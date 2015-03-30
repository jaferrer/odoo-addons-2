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
    'name': 'Stock Performance Improved',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Technical Settings',
    'depends': ['stock'],
    'description': """
Stock Performance Improved
==========================
Odoo is naturally optimized for situations where the stock is plenty and moves made on request with a relatively short
notice. This is typically the case of a retail store or a logistics company.

However, there are other situations where the stock is kept to minimum but the forecast moves are known well in
advance. This is typically the case of an industrial company with a long term planning applying just-in-time
procurement.

This module applies performance improvements for the second situation. Be aware that installing this module if you are
in the first situation might degrade performance instead of improving it.

Quants driven assignment
------------------------
In the case where stock are kept minimum, future procurements can create thousands of stock moves waiting for
availability which can lead to very slow assignments of quants to moves since all stock moves are checked each time,
even if there is only a few quants are made available.

This module changes the assignment logic so as to successively:

- Count the amount of each product in available quants
- Assign enough moves with this quantity and then stop

Transfer Improvements
---------------------
TODO
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}

