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
    'name': 'Génération des étiquettes de suivi',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Delivery Tracking',
    'depends': ['base', 'base_setup', 'sale', 'base_delivery_tracking', 'package_weight', 'report_aeroo'],
    'description': """
Génération des étiquettes de suivi
==================================
Ce module permet de générer des étiquettes d'envoi.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': ['security/ir.model.access.csv',
             'generate_tracking_labels.xml',
             'reports/reports.xml',
             'data.xml',
             'product.xml',
             'country.xml'],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
