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
    'name': 'Fields Permissions',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Hidden',
    'depends': [],
    'description': """
Fields Permissions
==================
Add a new mixin class, `fields.permissions.mixin`, that adds some parameters to odoo fields, in order to have finer
permissions on what field will or won't be read or written :

 * perm_read
 * perm_write
 * perm_rw, which combine both read and write permissions

Each of these paramters is treated as a new argument to a `fields` declaration, and can take, as value, either :

 * a boolean
 * a function reference (or a lambda function) taking self as parameter and returning a boolean
 * a string, referencing the name of a current model's method. The method should be @api.multi and return a boolean

An implementation of this can be seen in `test/field_permission_tester_example_class.py`

*Note : All fields are still readable/writable for `base.user_root` whatever their permissions are*
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
