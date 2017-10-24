# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

{
    'name': 'Mail Embedded Picture',
    'version': '1.0',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'website': 'https://www.ndp-systemes.fr/',
    'category': 'Mail',
    'depends': [
        'base',
        'web',
    ],
    'description': """
Mail Embedded Picture
=====================
The module includes the images of type 'ir.attachment' referenced in the body
of the email as part of the muli-part email. As a result, the mail no longer
contains html link to Odoo. The integration of images is made at when the
server sends the email to conserve disk space.
""",
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
}
