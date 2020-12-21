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
    'name': 'Widget Trigger Onchange',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'web',
    'depends': ['base'],
    'description': """
Widget Trigger Onchange
=======================
Adds a widget, displayed as a standard button. When this button is clicked, an onchange is triggered on the related
field.

This way, the button's changes are only temporary, and and discarded if the user clicks "cancel".

Usage
-----
```
<field name="my_boolean_field"
       widget="trigger_onchange"
       options="{'string': 'The button text', 'help': 'The button hover text'}"/>
```
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'views/templates.xml',
    ],
    'qweb': [
        "static/src/xml/trigger_onchange_template.xml",
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
