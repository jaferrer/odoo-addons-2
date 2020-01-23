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
    'name': 'SIRAIL hide required orderpoints',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Manufacturing',
    'depends': [
                'stock_mandatory_orderpoints',
                'stock_procurement_just_in_time', ],
    'description': """
SIRAIL hide required orderpoints
===============
 customisations for SIRAIL : hide required orderpoints field in Settings/Warehouse form
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'views/warehouse_settings.xml',
    ],
    'demo': [],
    'test': [],
    'do_not_update_noupdate_data_when_install': True,
    'installable': True,
    'auto_install': True,
    'license': 'AGPL-3',
    'application': False,
}
