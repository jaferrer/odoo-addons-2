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
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import job
from .models.bus_model_extend import BusImporter
from .connector import get_environment


@job(default_channel='root.receive_message')
def job_receive_message(session, model_name, backend_id, archive, wait_dependency=False):
    backend = session.env.ref("bus_integration.backend")
    msg = eval(archive)
    serial_id = int(msg.get("header").get("serial_id"))
    histo = session.env["busextend.backend.batch.histo"].search([('serial_id', '=', serial_id)], limit=1)
    if histo:
        histo_logs = session.env["busextend.backend.batch.histo.log"].search([('serial_id', '=', serial_id)])
        histo_logs.write({'state': 'DONE'})
    else:
        histo = session.env["busextend.backend.batch.histo"].create({
            "serial_id": serial_id,
            "name": "%s : %s > %s - %s" % (serial_id, msg.get("header").get("origin"), msg.get("header").get("dest"),
                                           msg.get("header").get("type_message_code")),
            "state": 'INPROGRESS'
        })
    if msg.get("header").get("type_message_code") in ["SIRAIL_SYNCHRO", "SIRAIL_SYNCHRO_DEPENDENCY"]:
        demand = recep_message_synchro(msg, session, backend)
        if demand:
            resp = {
                "body": {
                    "dependency": {},
                    "root": {},
                }
            }
            dest = msg.get("header").get("origin")
            resp["header"] = msg.get("header")
            resp["header"]["serial_id"] = msg.get("header").get("serial_id")
            resp["header"]["origin"] = msg.get("header").get("dest")
            resp["header"]["dest"] = dest
            resp["header"]["parent"] = msg.get("header").get("id")
            resp["header"]["type_message_code"] = "SIRAIL_SYNCHRO_DEMAND_DEPENDENCY"

            resp["body"]["demand"] = demand

            job_uid = generate_demand.delay(ConnectorSession.from_env(session.env), "bus.model.extend", 0, str(resp),
                                            code_recep=backend.code_recep_response,
                                            name="%s_%s" % (msg.get("header").get(
                                                "serial_id"), "demand_dependency_synchro"),
                                            description="%s_%s" % (
                msg.get("header").get("serial_id"), "Demand dependancy"))

            session.env["busextend.backend.batch.histo.log"].create({
                "histo_id": histo.id,
                "serial_id": histo.id,
                "log": u"SEND : DEMAND DEPENDENCY",
                "state": u"INPROGRESS",
                "job_uid": job_uid
            })
        else:
            resp = {
                "body": {
                    "dependency": {},
                    "root": {},
                }
            }
            dest = msg.get("header").get("origin")
            resp["header"] = msg.get("header")
            resp["header"]["serial_id"] = msg.get("header").get("serial_id")
            resp["header"]["origin"] = msg.get("header").get("dest")
            resp["header"]["dest"] = dest
            resp["header"]["type_message_code"] = "SIRAIL_SYNCHRO_RETURN"
            if msg.get("header").get("type_message_code") == "SIRAIL_SYNCHRO":
                resp["header"]["parent"] = msg.get("header").get("id")
                resp["body"]["return"] = {
                    "log": u"Intégration du message de synchro OK",
                    "state": u"DONE"
                }
            else:
                resp["header"]["parent"] = msg.get("header").get("parent")
                resp["body"]["return"] = {
                    "log": u"Intégration du message de synchro des dépendences OK",
                    "state": u"INPROGRESS"
                }
            job_uid = generate_response.delay(ConnectorSession.from_env(session.env), "bus.model.extend", 0, str(resp),
                                              code_recep=backend.code_recep_response,
                                              name="%s_%s" % (msg.get("header").get(
                                                  "serial_id"), "sirail_synchro_return"),
                                              description="%s %s" % (msg.get("header").get("serial_id"),
                                                                     "sirail synchro return"))
            session.env["busextend.backend.batch.histo.log"].create({
                "histo_id": histo.id,
                "serial_id": histo.id,
                "log": u"SEND : SYNCHRO RETURN",
                "state": u"INPROGRESS",
                "job_uid": job_uid
            })

    elif msg.get("header").get("type_message_code") == "SIRAIL_SYNCHRO_DEMAND_DEPENDENCY":
        log_recep = session.env["busextend.backend.batch.histo.log"].create({
            "histo_id": histo.id,
            "serial_id": histo.id,
            "log": u"RECEP : DEPENDENCY",
            "state": u"INPROGRESS"
        })
        resp = generate_message_demand_dependency(session, msg)
        job_uid = generate_response.delay(ConnectorSession.from_env(session.env), "bus.model.extend", 0, str(resp),
                                          code_recep=backend.code_recep_response,
                                          name="%s_%s" % (msg.get("header").get("serial_id"), "dependency_synchro"),
                                          description="%s %s" % (msg.get("header").get("serial_id"),
                                                                 "dependency synchro"))
        log_recep.write({'state': 'DONE'})
        session.env["busextend.backend.batch.histo.log"].create({
            "histo_id": histo.id,
            "serial_id": histo.id,
            "log": u"SEND : DEPENDENCY",
            "state": u"INPROGRESS",
            "job_uid": job_uid
        })
    elif msg.get("header").get("type_message_code") == "SIRAIL_SYNCHRO_RETURN":
        session.env["busextend.backend.batch.histo.log"].create({
            "histo_id": histo.id,
            "serial_id": histo.id,
            "log": u"RECEP : RETURN",
            "state": u"DONE"
        })
        if msg.get("body").get("return"):
            session.env["busextend.backend.batch.histo.log"].create({
                "histo_id": histo.id,
                "serial_id": histo.id,
                "log": msg.get("body").get("return").get("log"),
                "state": 'DONE'
            })
    elif msg.get("header").get("type_message_code") == "SIRAIL_SYNCHRO_DELETION":
        return_message = recep_message_synchro_deletion(msg, session, backend)
        resp = {
            "body": {
                "dependency": {},
                "root": {},
            }
        }
        dest = msg.get("header").get("origin")
        resp["header"] = msg.get("header")
        resp["header"]["serial_id"] = msg.get("header").get("serial_id")
        resp["header"]["origin"] = msg.get("header").get("dest")
        resp["header"]["dest"] = dest
        resp["header"]["parent"] = msg.get("header").get("id")
        resp["header"]["type_message_code"] = "SIRAIL_SYNCHRO_DELETION_RETURN"
        resp["body"]["return"] = return_message

        job_uid = generate_response.delay(ConnectorSession.from_env(session.env), "bus.model.extend", 0, str(resp),
                                          code_recep=backend.code_recep_response,
                                          name="%s_%s" % (msg.get("header").get("serial_id"), "dependency_synchro"),
                                          description="%s %s" % (msg.get("header").get("serial_id"),
                                                                 "dependency synchro"))
        session.env["busextend.backend.batch.histo.log"].create({
            "histo_id": histo.id,
            "serial_id": histo.id,
            "log": u"SEND : DELETION",
            "state": u"INPROGRESS",
            'job_uid': job_uid
        })
    elif msg.get("header").get("type_message_code") == "SIRAIL_SYNCHRO_DELETION_RETURN":
        session.env["busextend.backend.batch.histo.log"].create({
            "histo_id": histo.id,
            "serial_id": histo.id,
            "log": u"RECEP : RETURN",
            "state": u"DONE"
        })
        if msg.get("body").get("return"):
            session.env["busextend.backend.batch.histo.log"].create({
                "histo_id": histo.id,
                "serial_id": histo.id,
                "log": msg.get("body").get("return").get("log"),
                "state": 'DONE'
            })
        recep_message_synchro_deletion_return(msg, session, backend)
    else:
        return False
    return True


def recep_message_synchro_deletion_return(msg, session, backend):
    env = get_environment(session, 'bus.model.extend', backend.id)
    importer = env.get_connector_unit(BusImporter)
    dependencies = msg.get("body").get("dependency")
    res_deletion = msg.get("body").get("return")
    for key in res_deletion.keys():
        for item in res_deletion.get(key).values():
            importer.run_deletion_return(item, key, dependencies)
    return True


def recep_message_synchro_deletion(msg, session, backend):
    env = get_environment(session, 'bus.model.extend', backend.id)
    importer = env.get_connector_unit(BusImporter)
    dependencies = msg.get("body").get("dependency")
    root = msg.get("body").get("root")
    response = {}
    for key in root.keys():
        for item in root.get(key).values():
            unlink = importer.run_deletion(item, key, dependencies)
            if not response.get(item.get("_bus_model")):
                response[item.get("_bus_model")] = {}
            response[item.get("_bus_model")][str(item.get("id"))] = {
                "external_key": item.get("external_key"),
                "id": str(item.get("id")),
                "model": item.get("model"),
                "openerp_id": item.get("openerp_id"),
                "unlink": unlink
            }
    return response


def recep_message_synchro(msg, session, backend):
    env = get_environment(session, 'bus.model.extend', backend.id)
    importer = env.get_connector_unit(BusImporter)
    dependencies = msg.get("body").get("dependency")
    root = msg.get("body").get("root")
    demand = {}
    for key in dependencies.keys():
        for item in dependencies.get(key).values():
            # TODO : Implement import auto dependency (depedency already in the root dict, for parent_id for exemple)
            # remote_id = str(item.get('id', False))
            # item = root.get(key, False) and root.get(key, False).get(remote_id, False) or item
            dep = importer.run(item, key, dependencies)
            if dep:
                dep_model = dep.get("model", False) or dep.get("_bus_model", False)
                if dep.get("openerp_id") and dependencies.get(dep_model) and dependencies.get(dep_model).get(
                        dep.get("id")):
                    dependencies.get(dep_model).get(dep.get("id")).update({"openerp_id": dep.get("openerp_id")})
                if not demand.get(dep_model):
                    demand[dep_model] = {}
                demand[dep_model][str(item.get("id"))] = {
                    "external_key": dep.get("external_key"),
                    "id": str(item.get("id")),
                    "openerp_id": dep.get("openerp_id")
                }

    for key in root.keys():
        for item in root.get(key).values():
            importer.run(item, key, dependencies)
    return demand


def generate_message_demand_dependency(session, msg):
    resp = {
        "body": {
            "dependency": {},
            "root": {},
        }
    }
    dest = msg.get("header").get("origin")
    resp["header"] = msg.get("header")
    resp["header"]["serial_id"] = msg.get("header").get("serial_id")
    resp["header"]["origin"] = msg.get("header").get("dest")
    resp["header"]["dest"] = dest
    resp["header"]["type_message_code"] = "SIRAIL_SYNCHRO_DEPENDENCY"
    resp["header"]["parent"] = msg.get("header").get("parent")
    for key in msg.get("body").get("demand").keys():
        if key not in resp["body"]["dependency"]:
            resp["body"]["dependency"][key] = {}
        items = msg.get("body").get("demand").get(key)
        for id, item in items.iteritems():
            resp["body"]["dependency"][key][str(id)] = {
                "id": id
            }
            bus_model = session.env["object.mapping"].search([("name", "=", key)])
            map_field = session.env["object.mapping.field"].search([("export_field", '=', True),
                                                                    ("object_id", "=", bus_model.id)])
            item_odoo = session.env[key].browse(int(id))

            resp = session.env['busextend.backend.batch'].generate_dependency(resp, key, item_odoo.id)
            for field in map_field:
                value = getattr(item_odoo, field.name)
                if field.type_field == "M2O" and value:
                    resp["body"]["dependency"][key][str(item.get("id"))][field.map_name] = {
                        "id": value.id,
                        "model": field.relation
                    }
                elif field.type_field != "M2O" and value:
                    resp["body"]["dependency"][key][str(item.get("id"))][field.map_name] = value
    return resp


@job(default_channel='root.generate_response')
def generate_response(session, model_name, backend_id, archive, code_recep=False, name="rpc"):
    backend = session.env.ref("bus_integration.backend")
    tuple_result = backend.test_connexion(raise_error=True)
    args = [backend.db_odoo, tuple_result[1], backend.pwd, "recepteur", 'pull_odoo_sirail', code_recep, archive,
            name]
    _call_object_execute(tuple_result[0], args)
    return True


@job(default_channel='root.generate_demand')
def generate_demand(session, model_name, backend_id, archive, code_recep=False, name="rpc"):
    backend = session.env.ref("bus_integration.backend")

    tuple_result = backend.test_connexion(raise_error=True)
    args = [backend.db_odoo, tuple_result[1], backend.pwd, "recepteur", 'pull_odoo_sirail', code_recep, archive,
            name]
    _call_object_execute(tuple_result[0], args)
    return True


@job(default_channel='root.generate_message')
def job_generate_message(session, model_name, backend_id, ids_to_sync, code_recep=False, name="rpc"):
    backend = session.env.ref("bus_integration.backend")
    tuple_result = backend.test_connexion(raise_error=True)
    archive = str(session.env['busextend.backend.batch'].generate_message(ids_to_sync))
    args = [backend.db_odoo, tuple_result[1], backend.pwd, "recepteur", 'pull_odoo_sirail', code_recep, archive,
            name]
    _call_object_execute(tuple_result[0], args)
    return True


@job(default_channel='root.generate_message_deletion')
def generate_message_deletion(session, model_name, backend_id, ids_to_sync, code_recep=False, name="rpc"):
    backend = session.env.ref("bus_integration.backend")
    tuple_result = backend.test_connexion(raise_error=True)
    archive = str(session.env['busextend.backend.batch'].generate_message_deletion(ids_to_sync))
    args = [backend.db_odoo, tuple_result[1], backend.pwd, "recepteur", 'pull_odoo_sirail', code_recep, archive,
            name]
    _call_object_execute(tuple_result[0], args)
    return True


def _return_last_jsonrpclib_error():
    return json.loads(jsonrpclib.history.response).get('error').get('data').get('message')


def _call_object_execute(server, args):
    try:
        server.call(service="object", method="execute", args=args)
    except jsonrpclib.ProtocolError:
        raise FailedJobError(_return_last_jsonrpclib_error())
