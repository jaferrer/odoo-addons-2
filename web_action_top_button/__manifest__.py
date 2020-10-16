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
    'name': 'Action Top Buttons For Views',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Dependency',
    'depends': ['web'],
    'description': """
Action Top Buttons For Views
============================
This module enables action buttons to be put directly next to "Print" and "More" instead of having them necessarily
inside those menus.

Usage: set the group action_top_button to an user to have its button directly displayed.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'web_action_top_button.xml',
        'security/groups.xml',
    ],
    'demo': [],
    'qweb': [
        "static/src/xml/web_top_button_template.xml",
    ],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
