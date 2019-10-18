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
    'name': 'Outlook Sync',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Init',
    'depends': [
        'contacts',
        'calendar',
        'queue_job',
    ],
    'description': """
Outlook Sync
============
synchronize an Outlook email address with Odoo. This code needs you to create an app on Microsoft Azure :
- Go to https://portal.azure.com and log in with your address.
- Go to Azure Active Directory -> Apps registration -> New registration
- Choose "Accounts in any organizational directory (Any Azure AD directory - Multitenant) and personal Microsoft
  accounts (e.g. Skype, Xbox)" and your "Redirect URI" ex: http://localhost:XXXX/my_app or https if not local.
- Overview : Gives your client_id
- Authentication : To add new redirect URIs
- Certificates & secrets : Gives your client_secret (keep the value at creation, it's invisible after).
- API permissions : Determine the scopes allowed (see https://docs.microsoft.com/fr-fr/graph/permissions-reference)
See for more infos:
-> https://docs.microsoft.com/fr-fr/outlook/rest/get-started
-> https://docs.microsoft.com/fr-fr/previous-versions/office/office-365-api/api/version-2.0/calendar-rest-operations#
get-events
""",
    'website': 'http://www.ndp-systemes.fr',
    'demo': [],
    'test': [],
    'data': [
        'views/outlook_sync.xml',
        'views/cron.xml',
    ],
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
