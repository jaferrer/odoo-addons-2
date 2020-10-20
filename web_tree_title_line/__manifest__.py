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
    'name': 'Web Tree Title Line',
    'version': '1.0',
    'author': 'NDP Systèmes',
    'website': 'https://ndp-systemes.fr',
    'category': 'Web',
    'description': """
Web Tree Title Line
===================
Allows to create a title line in a tree view with a boolean field 'is_title_line' (see sale order lines v12)""",
    'depends': ['web'],
    'data': [
        'views/templates.xml',
    ],
    'installable': True,
    'application': True
}