# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
    'name': "Web Organization Chart",
    'description': """Display an organizational chart view of hierarchical objects""",
    'version': '1.0',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'website': 'http://www.ndp-systemes.fr',
    "category": "web",
    "application": False,
    'license': 'AGPL-3',
    "installable": True,
    'depends': [
        'web',
    ],
    'qweb': [
        'static/src/xml/web_organization_chart.xml',
    ],
    'data': [
        'views/web_organization_chart.xml',
    ],
}
