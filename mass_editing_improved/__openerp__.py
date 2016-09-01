# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
##############################################################################
{
    "name": "Mass Editing Improved",
    "version": "1.0",
    "author": "NDP Systemes",
    "category": "Tools",
    "website": "http://www.serpentcs.com",
    "license": "GPL-3 or any later version",
    "description": """
    This module provides the functionality to add, update or remove the values
    of more than one records on the fly at the same time.
    And now you can edit values of a sub record.
    """,
    'depends': ['mass_editing'],
    'data': [
        'views/mass_editing_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
