# -*- coding: utf-8 -*-
##############################################################################
#
#     This file is part of web_dialog_sizes, an Odoo module.
#
#     Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
#
#     web_expand_dialog is free software: you can redistribute it and/or
#     modify it under the terms of the GNU Affero General Public License
#     as published by the Free Software Foundation, either version 3 of
#     the License, or (at your option) any later version.
#
#     web_expand_dialog is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.
#
#     You should have received a copy of the
#     GNU Affero General Public License
#     along with web_expand_dialog.
#     If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': "Web list view group by improved",

    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'web',
    'depends': ['web'],
    'description': """Improved the group by function of the list view component
        """,
    'qweb': [
        'static/src/xml/web_listview_groupby_page.xml'
    ],
    'data': [
        'view/qweb.xml',
    ],
}
