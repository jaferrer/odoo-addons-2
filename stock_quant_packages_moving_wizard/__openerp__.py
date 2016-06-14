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
    'name': 'Quants and packaging moving wizards',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    "summary": "",
    "category": "Warehouse Management",
    "depends": [
        "stock"
    ],
    'description': """
Quants and packaging moving wizards
===================================
This module gives two possibilities to deplace quants. In one hand, you can do it by selecting them directly from "quants" menu, and in the other hand, by moving packages from "package" menu.
""",
    "website": "http://www.ndp-systemes.fr",
    "contributors": [
        "Oihane Crucelaegui <oihanecrucelaegi@avanzosc.es>",
        "Pedro M. Baeza <pedro.baeza@serviciosbaeza.com>",
        "Ana Juaristi <ajuaristio@gmail.com>"
    ],
    "data": [
        'security/ir.model.access.csv',
        "wizard/quant_move_wizard_view.xml",
        "wizard/quant_packages_move_wizard_view.xml",
        "wizard/product_line_move_wizard.xml",
        "views/stock.xml",
    ],
    'demo': [
        'test_stock_quant_packages_moving_wizard.xml',
    ],
    "installable": True,
}