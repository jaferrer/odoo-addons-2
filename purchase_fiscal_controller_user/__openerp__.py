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
    'name': 'Purchase - Fiscal Controller User',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Account',
    'depends': ['account_fiscal_controller_user', 'purchase_viewer'],
    'description': """
Purchase - Fiscal Controller User
=================================
This module adds acces rights to the user for fiscal administration, so that it is able to control purchases remotely
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': ['fiscal_controller_user.xml'],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': True,
    'license': 'AGPL-3',
    'application': False,
}
