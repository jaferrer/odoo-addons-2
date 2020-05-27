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
    'name': 'Odoo NDP HR Public Holidays',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Project',
    'depends': [
        'hr_holidays'
    ],
    'description': """
Odoo NDP HR Public Holidays
==========================
Ce module permet d'importer et d'utiliser les jours fériés français de la métropole.
Les jours fériés sont importés de :
- pour la France : https://www.data.gouv.fr/fr/datasets/jours-feries-en-france/ (url stables).
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'hr_public_holiday.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
