# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
    'name': 'MFA / IP Support',
    'summary': 'Allows users to enable MFA and add optional trusted devices',
    'version': '10.0.0.0.1',
    'category': 'Tools',
    'author': 'NDP systèmes',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'external_dependencies': {
        'python': ['pyotp'],
    },
    'depends': [
        'web',
    ],
    'data': [
        'data/ir_config_parameter.xml',
        'security/ir.model.access.csv',
        'security/res_users_authenticator_security.xml',
        'wizards/res_users_authenticator_create.xml',
        'views/auth_totp.xml',
        'views/res_users.xml',
    ],
}
