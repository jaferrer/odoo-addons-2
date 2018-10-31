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
    'name': 'Web Calendar Starred Domain',
    'category': 'Hidden',
    'description': """
Web Calendar Starred Domain.
============================
Change the native behavior of calendar views by introducing a new attribute for calendar views: starred_domain. It
allows to specify a domain in order to filter the partner that appear in the SidebarFilter (when you use the attribute
use_contacts).

""",
    'author': 'NDP Systèmes',
    'version': '2.0',
    'depends': ['web', 'web_calendar'],
    'data': [
        'views/web_calendar_templates.xml',
    ],
    'qweb': [
    ],
    'auto_install': False,
    'application': False
}
