# -*- coding: utf8 -*-
#
# Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
    'name': 'No Auto-Subscription of Partners',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Mail',
    'depends': ['mail'],
    'description': """
No Auto-Subscription of Partners
================================
Automatically remove partners that are not users from automatic subscription to objects.

This typically prevents customers from being automatically subscribed to their quotes, invoices, etc.

We use this hack because we can't inherit of an Abstract model

link to how and why we do that

http://stackoverflow.com/questions/31936122/how-to-inherit-mail-thread-abstractmodel-and-override-function-from-this-class-i

https://github.com/odoo/odoo/issues/9084
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
