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
    'name': 'Account Invoice Dunning',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Init',
    'depends': ['report_aeroo',
                'account'
                ],
    'description': """
Account Invoice Dunning
=======================
""",
    'website': 'http://www.ndp-systemes.fr',
    'demo': ['demo/dunning_demo.xml'],
    'test': [],
    'data': ['security/ir.model.access.csv',
             'views/dunning.xml',
             'views/dunning_type.xml',
             'views/dunning_invoice_link.xml',
             ],
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
