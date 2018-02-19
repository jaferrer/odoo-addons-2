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
    'name': 'Fixed colors for calendar',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Hidden',
    'depends': ['web_calendar'],
    'description': """
Fixed colors for calendar
=========================
This modules enables calendar colors based on formula.

Usage
-----
```
<calendar string="Events" date_start="date_start" date_stop="date_stop" colors="{red:alert==True;green:date_start<current_date}">
    <field name="name"/>
    <field name="alert" invisible="1"/>
</calendar>
```

""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'views/templates.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
