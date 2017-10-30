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
    'name': 'GitLab Integration for Odoo Issue Tracker',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Project',
    'depends': ['project_issue'],
    'description': """
GitLab Integration for Odoo Issue Tracker
=========================================
This modules integrates Odoo Issue Tracker with GitLab.

Howto use
---------
In GitLab, create a project.

In Odoo, create a project and go to the project form. In the GitLab integration tab:

- Fill in "GitLabURL" with your GitLab server URL (e.g. https://gitlab.exmaple.com)
- Fill in "API Token" with a authorized user GitLab private token (see Profile Settings->Account in GitLab).
- Click on "Update GitLab Projects List"
- Select the GitLab project in the list
- Click on "Setup GitLab integration for this project" to create the link with your GitLab project.

In GitLab, you can check that the "Custom Issue Tracker" service has been activated.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'security/ir.model.access.csv',
        'project_gitlab_view.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
