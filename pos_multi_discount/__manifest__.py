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
    "name": "POS Multi Discount",
    "summary": "POS Support of discount",
    "version": "0.1",
    "category": "Point Of Sale",
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "auto_install": True,
    "depends": [
        "point_of_sale",
        "pos_discount",
    ],
    'data': [
        'views/pos_config.xml',
        'views/product_view.xml',
        'views/assets.xml',
    ],
}
