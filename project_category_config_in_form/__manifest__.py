# -*- coding: utf8 -*-
#
# Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
    'name': 'Project Category Config In Form Compat',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Project',
    'depends': ['project_task_category', 'project_config_in_form'],
    'description': """
Compatibility between project_portal and project_task_sequence
==============================================================
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': ['compat_views.xml'],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': True,
    'license': 'AGPL-3',
    'application': False,
}
