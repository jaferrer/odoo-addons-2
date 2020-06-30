# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
    'name': 'Form List View Sticky Header',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'web',
    'description': """
Form List View Sticky Header
============================
""",
    'website': 'http://www.ndp-systemes.fr',
        'depends': ['base'],

    'data': [
        'views/assets.xml',
    ],
    'qweb': [
        "static/src/xml/qweb.xml",
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': True,
    'license': 'AGPL-3',
    'application': False,
}