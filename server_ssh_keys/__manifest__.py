# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
    'name': 'SSH Keys management',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Technical Settings',
    'depends': ['web'],
    'description': """
SSH Keys management
===================
This modules allows server SSH keys management.

User public keys are stored in Odoo. The `/ssh/<server_name>/<role_name>` controllers return the authorized keys
for the given role on the given server. This controller can be used as part of a SSH AuthorizedKeysCommand.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'security/ssh_security.xml',
        'security/ir.model.access.csv',
        'views/key.xml',
        'views/role.xml',
        'views/server.xml',
        'views/res_users.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
