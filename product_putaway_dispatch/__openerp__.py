# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
    'name': 'Product Dispatch',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': '',
    'depends': ['stock'],
    'description': """
Product Dispatch
================
This modules adds a new button "Dispatch" to the transfer dialog of a stock operation. This buttons dispatches the
products according to their needs in the different children locations of the original destination location. The operator
has the opportunity to modify the dispatch that has been done this way before validating the transfer.

If no need is found in any of the child locations, the product is sent back to the source location so as to unreserve
it.

This button only appears if the original destination location has its putaway strategy set to a strategy of type
"Dispatch". Strategies of type "Dispatch" need only to be defined once and can be applied to several locations.
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'product_putaway_dispatch_view.xml'
    ],
    'demo': [
        'product_putaway_dispatch_demo.xml'
    ],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
