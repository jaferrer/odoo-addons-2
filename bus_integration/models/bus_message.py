# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp.addons.connector.session import ConnectorSession

from openerp import models, fields, api
from ..connector.jobs import generate_demand, generate_response
from ..connector.bus_importer import BusImporter


class BusMessage(models.Model):
    _name = 'bus.message'

    done = fields.Boolean(u"Done")
    date_done = fields.Datetime(u"Date Done")
    header_param_ids = fields.One2many('bus.message.header.param', 'message_id', u"Header parameters")
    body = fields.Text(u"Body")
    extra_content = fields.Text(u"Extra-content")
    type = fields.Selection([('received', u"Received"), ('sent', u"Sent")], u"Message Type", required=True)
    treatment = fields.Selection([('synchronization', u"Synchronization"),
                                  ('DEPENDENCY_SYNCRONIZATION', u"Dependency synchronization"),
                                  ('DEPENDENCY_DEMAND_SYNCHRONIZATION', u"Dependency demand sychronization"),
                                  ('SYNCHRONIZATION_RETURN', u"Synchronization return"),
                                  ('DELETION_SYNCHRONIZATION', u"Deletion synchronization"),
                                  ('DELETION_SYNCHRONIZATION_RETURN', u"Deletion synchronization return"),
                                  ], u"Treatment", required=True)

    @api.multi
    def name_get(self):
        return [(rec.id, u"Message received on %s" % rec.create_date) for rec in self]

    @api.multi
    def process_received_message(self, backend, histo, message_dict):
        result = True
        if message_dict.get('header').get('treatment') in ['synchronization', 'DEPENDENCY_SYNCRONIZATION']:
            demand = self.recep_message_synchro(message_dict)
            if demand:
                self.send_dependancy_demand(backend, message_dict, demand, histo)
            else:
                self.send_synchro_return_message(backend, message_dict, histo)
        elif message_dict.get('header').get('treatment') == 'DEPENDENCY_DEMAND_SYNCHRONIZATION':
            self.send_dependency_demand_message(backend, message_dict, histo)
        elif message_dict.get('header').get('treatment') == 'SYNCHRONIZATION_RETURN':
            self.register_synchro_return(message_dict, histo)
        elif message_dict.get('header').get('treatment') == 'DELETION_SYNCHRONIZATION':
            self.send_deletion_return_message()
        elif message_dict.get('header').get('treatment') == 'DELETION_SYNCHRONIZATION_RETURN':
            self.register_synchro_deletion_return(message_dict, histo)
        else:
            result = False
        self.write({'done': True})
        return result

    @api.model
    def create_message(self, message_dict, type):
        # message_dict is a JSON loaded dict.
        if not message_dict:
            message_dict = {}
        extra_content_dict = {key: message_dict[key] for key in message_dict if key not in ['body', 'header']}
        message = self.create({
            'body': message_dict.get('body', """"""),
            'extra_content': extra_content_dict and json.dumps(extra_content_dict, indent=4) or """""",
            'type': type,
            'treatment': message_dict.get('header', {}).get('treatment')
        })
        for key, value in message.get('header', {}).iteritems():
            if key == 'treatment':
                continue
            self.env['bus.message.header.param'].create({
                'message_id': message.id,
                'name': key,
                'value': value,
            })
        return message

    @api.model
    def recep_message_synchro_deletion_return(self, message_dict):
        importer = self.env.get_connector_unit(BusImporter)
        dependencies = message_dict.get('body').get('dependency')
        res_deletion = message_dict.get('body').get('return')
        for key in res_deletion.keys():
            for item in res_deletion.get(key).values():
                importer.run_deletion_return(item, key, dependencies)
        return True

    def recep_message_synchro_deletion(self, message_dict, backend):
        importer = self.env.get_connector_unit(BusImporter)
        dependencies = message_dict.get('body').get('dependency')
        root = message_dict.get('body').get('root')
        response = {}
        for key in root.keys():
            for item in root.get(key).values():
                unlink = importer.run_deletion(item, key, dependencies)
                if not response.get(item.get('_bus_model')):
                    response[item.get('_bus_model')] = {}
                response[item.get('_bus_model')][str(item.get('id'))] = {
                    'external_key': item.get('external_key'),
                    'id': str(item.get('id')),
                    'model': item.get('model'),
                    'local_id': item.get('local_id'),
                    'unlink': unlink
                }
        return response

    def recep_message_synchro(self, message_dict):
        importer = self.env.get_connector_unit(BusImporter)
        dependencies = message_dict.get('body').get('dependency')
        root = message_dict.get('body').get('root')
        demand = {}
        for key in dependencies.keys():
            for item in dependencies.get(key).values():
                # TODO : Implement import auto dependency (depedency already in the root dict, for parent_id for exemple)
                # remote_id = str(item.get('id', False))
                # item = root.get(key, False) and root.get(key, False).get(remote_id, False) or item
                dep = importer.run(item, key, dependencies)
                if dep:
                    dep_model = dep.get('model', False) or dep.get('_bus_model', False)
                    if dep.get('local_id') and dependencies.get(dep_model) and dependencies.get(dep_model).get(
                            dep.get('id')):
                        dependencies.get(dep_model).get(dep.get('id')).update({'local_id': dep.get('local_id')})
                    if not demand.get(dep_model):
                        demand[dep_model] = {}
                    demand[dep_model][str(item.get('id'))] = {
                        'external_key': dep.get('external_key'),
                        'id': str(item.get('id')),
                        'local_id': dep.get('local_id')
                    }

        for key in root.keys():
            for item in root.get(key).values():
                importer.run(item, key, dependencies)
        return demand

    @api.model
    def send_dependancy_demand(self, backend, message_dict, demand, histo):
        resp = {
            'body': {
                'dependency': {},
                'root': {},
            }
        }
        dest = message_dict.get('header').get('origin')
        resp['header'] = message_dict.get('header')
        resp['header']['serial_id'] = message_dict.get('header').get('serial_id')
        resp['header']['origin'] = message_dict.get('header').get('dest')
        resp['header']['dest'] = dest
        resp['header']['parent'] = message_dict.get('header').get('id')
        resp['header']['treatment'] = 'DEPENDENCY_DEMAND_SYNCHRONIZATION'
        resp['body']['demand'] = demand
        description = u"%s_%s" % (message_dict.get('header').get('serial_id'), 'Demand dependancy')
        self.create_message(resp, type='sent')
        job_uid = generate_demand.delay(ConnectorSession.from_env(self.env), 'bus.receive.transfer', 0, str(resp),
                                        bus_reception_treatment=backend.reception_treatment,
                                        name='%s_%s' % (message_dict.get('header').get(
                                            'serial_id'), 'demand_dependency_synchro'),
                                        description=description)

        self.env['bus.backend.batch.histo.log'].create({
            'histo_id': histo.id,
            'serial_id': histo.id,
            'log': u'SEND : DEMAND DEPENDENCY',
            'state': 'running',
            'job_uid': job_uid
        })

    @api.model
    def send_synchro_return_message(self, backend, message_dict, histo):
        resp = {
            'body': {
                'dependency': {},
                'root': {},
            }
        }
        dest = message_dict.get('header').get('origin')
        resp['header'] = message_dict.get('header')
        resp['header']['serial_id'] = message_dict.get('header').get('serial_id')
        resp['header']['origin'] = message_dict.get('header').get('dest')
        resp['header']['dest'] = dest
        resp['header']['treatment'] = 'SYNCHRONIZATION_RETURN'
        if message_dict.get('header').get('treatment') == 'synchronization':
            resp['header']['parent'] = message_dict.get('header').get('id')
            resp['body']['return'] = {
                'log': u'Intégration du message de synchro OK',
                'state': u'done'
            }
        else:
            resp['header']['parent'] = message_dict.get('header').get('parent')
            resp['body']['return'] = {
                'log': u'Intégration du message de synchro des dépendences OK',
                'state': u'running'
            }
        job_uid = generate_response.delay(ConnectorSession.from_env(self.env), 'bus.receive.transfer', 0, str(resp),
                                          bus_reception_treatment=backend.reception_treatment,
                                          name=u"%s_%s" % (message_dict.get('header').get(
                                              'serial_id'), 'synchro_return'),
                                          description=u"%s %s" % (message_dict.get('header').get('serial_id'),
                                                                  u"Synchronization return"))
        self.env['bus.backend.batch.histo.log'].create({
            'histo_id': histo.id,
            'serial_id': histo.id,
            'log': u'SEND : SYNCHRO RETURN',
            'state': u'running',
            'job_uid': job_uid
        })

    @api.model
    def send_dependency_demand_message(self, backend, message_dict, histo):
        log_recep = self.env['bus.backend.batch.histo.log'].create({
            'histo_id': histo.id,
            'serial_id': histo.id,
            'log': u'RECEP : DEPENDENCY',
            'state': u'running'
        })
        resp = {
            'body': {
                'dependency': {},
                'root': {},
            }
        }
        dest = message_dict.get('header').get('origin')
        resp['header'] = message_dict.get('header')
        resp['header']['serial_id'] = message_dict.get('header').get('serial_id')
        resp['header']['origin'] = message_dict.get('header').get('dest')
        resp['header']['dest'] = dest
        resp['header']['treatment'] = 'DEPENDENCY_SYNCRONIZATION'
        resp['header']['parent'] = message_dict.get('header').get('parent')
        for key in message_dict.get('body').get('demand').keys():
            if key not in resp['body']['dependency']:
                resp['body']['dependency'][key] = {}
            items = message_dict.get('body').get('demand').get(key)
            for id, item in items.iteritems():
                resp['body']['dependency'][key][str(id)] = {
                    'id': id
                }
                bus_model = self.env['bus.object.mapping'].get_mapping(key)
                map_field = self.env['bus.object.mapping.field'].search([('export_field', '=', True),
                                                                           ('mapping_id', '=', bus_model.id)])
                item_odoo = self.env[key].browse(int(id))

                resp = self.env['bus.backend.batch'].generate_dependency(resp, key, item_odoo.id)
                for field in map_field:
                    value = getattr(item_odoo, field.name)
                    if field.type_field == 'many2one' and value:
                        resp['body']['dependency'][key][str(item.get('id'))][field.map_name] = {
                            'id': value.id,
                            'model': field.relation
                        }
                    elif field.type_field != 'many2one' and value:
                        resp['body']['dependency'][key][str(item.get('id'))][field.map_name] = value
        job_uid = generate_response.delay(ConnectorSession.from_env(self.env), 'bus.receive.transfer', 0, str(resp),
                                          bus_reception_treatment=backend.reception_treatment,
                                          name='%s_%s' % (
                                          message_dict.get('header').get('serial_id'), 'dependency_synchro'),
                                          description='%s %s' % (message_dict.get('header').get('serial_id'),
                                                                 'dependency synchro'))
        log_recep.write({'state': 'done'})
        self.env['bus.backend.batch.histo.log'].create({
            'histo_id': histo.id,
            'serial_id': histo.id,
            'log': u'SEND : DEPENDENCY',
            'state': u'running',
            'job_uid': job_uid
        })

    @api.model
    def register_synchro_return(self, message_dict, histo):
        self.env['bus.backend.batch.histo.log'].create({
            'histo_id': histo.id,
            'serial_id': histo.id,
            'log': u'RECEP : RETURN',
            'state': u'done'
        })
        if message_dict.get('body').get('return'):
            self.env['bus.backend.batch.histo.log'].create({
                'histo_id': histo.id,
                'serial_id': histo.id,
                'log': message_dict.get('body').get('return').get('log'),
                'state': 'done'
            })

    @api.model
    def send_deletion_return_message(self, backend, message_dict, histo):
        return_message = self.recep_message_synchro_deletion(message_dict, backend)
        resp = {
            'body': {
                'dependency': {},
                'root': {},
            }
        }
        dest = message_dict.get('header').get('origin')
        resp['header'] = message_dict.get('header')
        resp['header']['serial_id'] = message_dict.get('header').get('serial_id')
        resp['header']['origin'] = message_dict.get('header').get('dest')
        resp['header']['dest'] = dest
        resp['header']['parent'] = message_dict.get('header').get('id')
        resp['header']['treatment'] = 'DELETION_SYNCHRONIZATION_RETURN'
        resp['body']['return'] = return_message

        job_uid = generate_response.delay(ConnectorSession.from_env(self.env), 'bus.receive.transfer', 0, str(resp),
                                          bus_reception_treatment=backend.reception_treatment,
                                          name='%s_%s' % (
                                          message_dict.get('header').get('serial_id'), 'dependency_synchro'),
                                          description='%s %s' % (message_dict.get('header').get('serial_id'),
                                                                 'dependency synchro'))
        self.env['bus.backend.batch.histo.log'].create({
            'histo_id': histo.id,
            'serial_id': histo.id,
            'log': u'SEND : deletion',
            'state': u'running',
            'job_uid': job_uid
        })

    @api.model
    def register_synchro_deletion_return(self, message_dict, histo):
        self.env['bus.backend.batch.histo.log'].create({
            'histo_id': histo.id,
            'serial_id': histo.id,
            'log': u'RECEP : RETURN',
            'state': u'done'
        })
        if message_dict.get('body').get('return'):
            self.env['bus.backend.batch.histo.log'].create({
                'histo_id': histo.id,
                'serial_id': histo.id,
                'log': message_dict.get('body').get('return').get('log'),
                'state': 'done'
            })
        self.recep_message_synchro_deletion_return(message_dict)

    @api.model
    def create(self, vals):
        if vals.get('done'):
            vals['date_done'] = fields.Datetime.now()
        return super(BusMessage, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('done'):
            vals['date_done'] = fields.Datetime.now()
        return super(BusMessage, self).write(vals)


class BusMessageHearderParam(models.Model):
    _name = 'bus.message.header.param'

    message_id = fields.Many2one('bus.message', u"Message", required=True)
    name = fields.Char(u"Key", required=True)
    value = fields.Char(u"Value", required=True)
