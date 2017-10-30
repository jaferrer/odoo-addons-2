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
    'name': 'Fix barcode scanner interface',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': '',
    'depends': ['stock'],
    'description': """
This module is a temporary fix before https://github.com/odoo/odoo/pull/4637 is pulled upstream.

It also tries to improve speed by fetching stock locations only when necessary.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'fix_barcode_scanner.xml'
    ],
    'demo': [],
    'test': [],
    'installable': False,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}

