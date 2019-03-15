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

import json
import jsonrpclib

from openerp.addons.connector.exception import FailedJobError
from openerp.addons.connector.queue.job import job


@job(default_channel='root.receive_message')
def job_receive_message(session, model_name, backend_id, message_dict, message_id):
    backend = session.env[model_name].browse(backend_id)
    backend.ensure_one()
    # TODO: revoir le fonctionnement des histo.
    histo = session.env['bus.backend.batch.histo'].create_histo_if_needed(message_dict)
    message = session.env['bus.message'].search([('id', '=', message_id)])
    return message.process_received_message(backend, histo, message_dict)

@job(default_channel='root.generate_response')
def generate_response(session, model_name, backend_id, message, bus_reception_treatment=False, name='rpc'):
    backend = session.env[model_name].browse(backend_id)
    server, connexion_result = backend.test_connexion()
    args = [backend.db_odoo, connexion_result, backend.password, 'recepteur', 'classical_reception', bus_reception_treatment,
            message, name]
    _call_object_execute(server, args)
    return True


@job(default_channel='root.generate_demand')
def generate_demand(session, model_name, backend_id, message, bus_reception_treatment=False, name='rpc'):
    backend = session.env[model_name].browse(backend_id)
    server, connexion_result = backend.test_connexion()
    args = [backend.db_odoo, connexion_result, backend.password, 'recepteur', 'classical_reception', bus_reception_treatment,
            message, name]
    _call_object_execute(server, args)
    return True


@job(default_channel='root.generate_message')
def job_generate_message(session, model_name, backend_id, ids_to_sync, bus_reception_treatment=False, name='rpc', deletion=False):
    backend = session.env[model_name].browse(backend_id)
    server, connexion_result = backend.test_connexion()
    message = str(session.env['bus.backend.batch'].generate_message(ids_to_sync, deletion=deletion))
    args = [backend.db_odoo, connexion_result, backend.password, 'recepteur', 'classical_reception', bus_reception_treatment,
            message, name]
    _call_object_execute(server, args)
    return True


def _return_last_jsonrpclib_error():
    return json.loads(jsonrpclib.history.response).get('error', {}).get('data', {}).get('message', "")


def _call_object_execute(server, args):
    try:
        server.call(service='object', method='execute', args=args)
    except jsonrpclib.ProtocolError:
        raise FailedJobError(_return_last_jsonrpclib_error())
