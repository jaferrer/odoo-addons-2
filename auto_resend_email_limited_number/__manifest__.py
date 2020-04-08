# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
    'name': 'Auto Resend Emails - Limited Numbers',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Init',
    'depends': ['auto_resend_mail', 'queue_job_cron'],
    'description': """
Auto Resend Emails - Limited Numbers
====================================
This module re-launches, once per day, failed emails. After 5 launches, it makes a queue_job swith to failed.
""",
    'website': 'http://www.ndp-systemes.fr',
    'demo': [],
    'test': [],
    'data': [
        'cron.xml',
        'mail.xml',
    ],
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
