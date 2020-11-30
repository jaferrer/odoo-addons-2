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
    'name': 'Role Delegation',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Manufacture',
    'depends': [
        'hr',
        'base_user_role'
    ],
    'description': """
Role Delegation
===============
Allows res.users to delegate all their roles to other users, for a limited period of time
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'data/delegation_notification_subtype.xml',
        'data/notification_templates.xml',
        'views/role_delegation.xml',
        'views/res_users.xml',
        'views/hr_employee.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
    ],
    'external_dependencies': {
        'python': [
            'freezegun',
        ],
    },
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
