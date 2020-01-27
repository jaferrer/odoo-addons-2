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
    'name': 'Calendar SMS reminders',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Project',
    'depends': ['base', 'calendar'],
    'external_dependencies': {'python': ['phonenumbers', 'octopush']},
    'description': """
SEND SMS FROM CALENDAR EVENTS
===============================
requirements: octopush sms plateform subscription
configuration: go to company settings in the SMS tab and define the SMS API login and key
usage: open a calendar event and clic on `send SMS` button.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'views/sms_wizard.xml',
        'views/calendar.xml',
        'views/company.xml',
    ],
    'qweb': [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
