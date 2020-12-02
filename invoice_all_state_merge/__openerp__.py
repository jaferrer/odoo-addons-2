# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

{
    'name': 'Invoice merge in all state',
    'version': '1.0',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'website': 'https://www.ndp-systemes.fr/',
    'category': 'Account',
    'depends': ['account_invoice_merge'],
    'data': ['views.xml'],
    'description': """
Invoice merge in all state
==========================
This Module allow to merge invoice even if the state is payed or open""",
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
}
