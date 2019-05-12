# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp.addons.connector.queue.job import job


@job(default_channel='root.receive_message')
def job_receive_message(session, model_name, message_id):
    return session.env[model_name].process_received_message(message_id)


@job(default_channel='root.send_response')
def job_send_response(session, model_name, configuration_id, message):
    backend = session.env[model_name].browse(configuration_id)
    return backend.send_odoo_message('bus.message', 'odoo_synchronization_bus', backend.reception_treatment,
                                     message)


@job(default_channel='root.generate_message')
def job_generate_message(session, model_name, bus_configuration_export_id, export_msg, bus_reception_treatment=False,
                         deletion=False):
    return session.env[model_name].generate_message(bus_configuration_export_id, export_msg, bus_reception_treatment,
                                                    deletion=deletion)
