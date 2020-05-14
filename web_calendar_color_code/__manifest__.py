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
    'name': 'Color Code for Calendar View',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Hidden',
    'depends': ['web_calendar'],
    'description': """
Color Code for Calendar View
============================
This function adds a `color_code` attribute to the calendar tag, that allows to specify a field on the model containing
the color code (any valid css code) to apply to each cell.
It is different from the "color" field, in that it allows to chose the color instead of having a pseudorandom one.

Usage
-----
```
<calendar ... color_code="my_color_field">
    <field name="name"/>
</calendar>
```

""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'views/templates.xml',
    ],
    'qweb': [
        'static/src/xml/qweb.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
