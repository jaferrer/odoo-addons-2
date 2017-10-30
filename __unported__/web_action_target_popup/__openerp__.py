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
    'name': 'Popup Target for Actions',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Dependency',
    'depends': ['web'],
    'description': """
Popup Target for Actions
========================
This module adds a new target "popup" for actions alongside "new" and "current". This new "popup" target opens the
action in a new window but does not close the previous action window if this was already a pop-up window.

Usage: set target="popup" in actions opened from an action that has a target "new".

Notes:

- Calling an action with target="popup" from the main window has the same effect as calling it with target="new"
- For the moment, this only works for one level depth, i.e. for a popup window opened in another popup window.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'web_action_target_popup.xml',
    ],
    'demo': [],
    'test': [],
    'installable': False,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
