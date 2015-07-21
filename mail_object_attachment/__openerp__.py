#
#   Copyright (C) 2008-2015 by Nicolas Piganeau
#   npi@m4x.org
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the
#   Free Software Foundation, Inc.,
#   59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

{
    'name': 'Send Object Attachments by Email',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Usability',
    'depends': ['email_template'],
    'description': """
Send Object Attachments by Email
================================
This module adds an option "Attach object attachments" to email templates. When this option is selected, all the
attachments of the object will be added to the email attachments.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'mail_object_attachment_view.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
