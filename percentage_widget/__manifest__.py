# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
    'name': 'Web Tree Fix',
    'version': '1.0',
    'author': 'NDP Systèmes',
    'website': 'https://ndp-systemes.fr',
    'category': 'Web',
    'description': """
Web Tree Fix
============
Feature:
Percentage widget for list view and form view -> 1.25 = + 25.00% ; 0.75 = - 25.00% ; 0 = 0.00%
How to use:
- Adding widget="percent" attribute for your Float field on view
Ex: <field name="commission" widget="percent" />""",
    'depends': ['web'],
    'data': [
        'views/templates.xml',
    ],
    'installable': True,
    'application': True
}
