# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: JB Aubort
#    Copyright 2008 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{'name': 'Invoice Interco',
 'version': '1.0',
 'author': 'NDP Systèmes',
 'maintainer': 'NDP Systèmes',
 'category': 'Generic Modules/Human Resources',
 'description': """
Module to create reverse invoice inside a multi company
=======================================================

This module create a 'in_invoice' type when a 'out_invoice' type is validate and the customer is an internal compagny
""",
 'license': 'AGPL-3',
 'depends': [
     'account',
 ],
 'data': [
     'views/views.xml'
 ],
 'demo': [
     'data/data.xml'
 ],
 'installable': True,
 'auto_install': False,
 'application': False,
 }
