# -*- coding: utf8 -*-
#
#    Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
    'name': 'Connector to Odoo Databus',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Technical',
    'depends': [
        'connector',
        'web_sheet_full_width_selective',
        'bus_send_message',
    ],
    'description': """
Connector to Odoo Databus
=========================
Connector to Odoo Databus
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'security/ir.model.access.csv',
        'data/bus_configuration.xml',
        'views/bus_receive_transfer.xml',
        'views/bus_check_transfer.xml',
        'views/bus_configuration.xml',
        'views/bus_configuration_export.xml',
        'views/bus_base.xml',
        'views/bus_message.xml',
        'views/bus_message_log.xml',
        'views/bus_object_mapping.xml',
        'views/mapping_configuration_helper.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
