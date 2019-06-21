# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
import datetime
import collections
from openerp import models, api, exceptions
from openerp.tools import safe_eval
from openerp.addons.connector.session import ConnectorSession
from ..connector.jobs import job_generate_message


class BusSynchronizationExporter(models.AbstractModel):
    _name = 'bus.exporter'

    authorize_field_type = ['char', 'boolean', 'date', 'datetime', 'float', 'html', 'integer', 'text', 'selection', ]

    # TODO :  a vérifier :  'binary', 'reference', 'serialized]

    @api.model
    def run_export(self, backend_bus_configuration_export_id, force_domain=[]):
        """
        Create and send messages
        :param backend_bus_configuration_export_id: models to export with their conf
        :param deletion: treatment type deletion ?
        :return: True or raise an exception
        """
        batch = self.env['bus.configuration.export'].browse(backend_bus_configuration_export_id)
        object_mapping = self.env['bus.object.mapping'].search([('model_name', '=', batch.model)])
        if not object_mapping or not object_mapping.is_exportable:
            raise exceptions.ValidationError(u"Object mapping not configured for model : %s" % batch.model)

        # last_send_date: limit the number models to synchronise, we only send models which have been updated after the
        #                 last export bus.configuration.export domain should be set to
        #                 [('write_date', '>', last_send_date)]
        export_domain = batch.domain and safe_eval(batch.domain, batch.export_domain_keywords()) or []

        if batch.treatment_type != 'DELETION_SYNCHRONIZATION' and object_mapping.deactivated_sync and \
                'active' in self.env[batch.model]._fields:
            export_domain += ['|', ('active', '=', False), ('active', '=', True)]
        if force_domain:
            force_domain = safe_eval(force_domain, batch.export_domain_keywords())
            export_domain += force_domain

        ids_to_export = self.env[batch.model].search(export_domain)
        if not ids_to_export:
            histo = batch.get_histo(str(ids_to_export))
            batch.serial_id = histo.id
            histo.add_log(False, self.env.context.get('job_uuid'), log="no id to export")
            histo.transfer_state = 'finished'
            return True

        message_list = []
        message_dict = {
            'header': {
                'origin': batch.configuration_id.sender_id.bus_username,
                'dest': batch.recipient_id.bus_username,
                'treatment': batch.treatment_type,
                'serial_id': batch.serial_id,
            },
            'export': None
        }
        export_chunk = batch.chunk_size or False
        if export_chunk:
            while ids_to_export:
                chunk = ids_to_export[:export_chunk]
                ids_to_export = ids_to_export[export_chunk:]
                chunk_message = message_dict.copy()
                chunk_message['export'] = {
                    'model': chunk._name,
                    'ids': chunk.ids
                }
                message_list.append(chunk_message)
        else:
            message_dict['export'] = {
                'model': ids_to_export._name,
                'ids': ids_to_export.ids
            }
            message_list.append(message_dict)

        for export_msg in message_list:
            job_generate_message.delay(ConnectorSession.from_env(self.env), self._name, batch.id,
                                       export_msg, bus_reception_treatment=batch.bus_reception_treatment)
        return True

    @api.model
    def generate_message(self, bus_configuration_export_id, export_msg, bus_reception_treatment):
        batch = self.env['bus.configuration.export'].browse(bus_configuration_export_id)
        message_dict = collections.OrderedDict()
        message_dict['header'] = export_msg.get('header')
        message_dict['body'] = {
            'root': {},
            'dependency': {},
        }
        model_name = export_msg.get('export').get('model')
        ids = export_msg.get('export').get('ids')
        histo = batch.get_histo(str(ids))
        batch.serial_id = histo.id
        message_dict['header']['serial_id'] = histo.id
        message_dict['header']['bus_configuration_export_id'] = batch.id
        exported_records = self.env[model_name].search([('id', 'in', ids)])
        message_type = message_dict.get('header').get('treatment')
        if message_type == 'DELETION_SYNCHRONIZATION':
            result = self._generate_msg_body_deletion(exported_records, model_name)
        elif message_type == 'CHECK_SYNCHRONIZATION':
            result = self._generate_check_msg_body(exported_records, model_name, message_dict['header']['dest'])
        else:
            result = self._generate_msg_body(exported_records, model_name)
        message_dict['body'] = result['body']
        message = self.env['bus.message'].create_message(message_dict, 'sent', batch.configuration_id)

        message_json = json.dumps(message_dict, encoding='utf-8')
        send_result = batch.configuration_id.send_odoo_message('bus.message', 'odoo_synchronization_bus',
                                                               bus_reception_treatment, message_json)
        histo.add_log(message.id, self.env.context.get('job_uuid'), log=send_result)

    # region def _generate_msg_body(self, exported_records, model_name):
    def _generate_msg_body(self, exported_records, model_name):
        message_dict = {
            'body': {
                'root': {},
                'dependency': {},
            }
        }
        object_mapping = self.env['bus.object.mapping'].get_mapping(model_name)
        if not object_mapping:
            raise exceptions.ValidationError('bus.object.mapping not defined for model %s ' % model_name)
        for record in exported_records:
            record_id = str(record.id)
            if model_name not in message_dict['body']['root']:
                message_dict['body']['root'][model_name] = {}
            message_dict['body']['root'][model_name][record_id] = {'id': record.id}
            if object_mapping.key_xml_id:
                xml_id = self.get_xml_id(model_name, record.id)
                if xml_id:
                    message_dict['body']['root'][model_name][record_id]['xml_id'] = xml_id
            list_export_field = object_mapping.get_field_to_export()
            for field in list_export_field:
                if field.type_field == 'many2many' and record[field.field_name].ids:
                    message_dict = self.fill_many2many(message_dict, record, field)
                if field.type_field == 'many2one' and record[field.field_name].id:
                    message_dict = self.fill_many2one(message_dict, record, field)
                elif field.type_field in self.authorize_field_type:
                    message_dict = self.fill_field(message_dict, record, field)
        return message_dict

    @api.model
    def get_xml_id(self, model, record_id):
        ir_model_data = self.env['ir.model.data'].search([('model', '=', model),
                                                          ('res_id', '=', record_id)])
        return ir_model_data and ir_model_data.complete_name or False

    @api.model
    def fill_field(self, message_dict, record, field):
        record_id = str(record.id)
        message_dict['body']['root'][record._name][record_id][field.map_name] = record[field.field_name]
        if field.field_id.ttype == 'char' and field.field_id.translate:
            translation_name = "%s,%s" % (record._name, field.field_name)
            translations = self.env['ir.translation'].search([('name', '=', translation_name),
                                                              ('res_id', '=', record.id)])
            if translations:
                message_dict = self.fill_translation(message_dict, record._name, record_id, field, translations)
        return message_dict

    @api.model
    def fill_many2one(self, message_dict, record, field):
        record_id = str(record.id)
        message_dict['body']['root'][record._name][record_id][field.map_name] = {
            'id': record[field.field_name].id,
            'model': field.relation,
            'type_field': 'many2one'
        }
        sub_record = record[field.field_name]
        message_dict = self.fill_dependancy(message_dict, field.relation, sub_record)
        return message_dict

    @api.model
    def fill_many2many(self, message_dict, record, field):
        record_id = str(record.id)
        message_dict['body']['root'][record._name][record_id][field.map_name] = {
            'ids': record[field.field_name].ids,
            'model': field.relation,
            'type_field': 'many2many'
        }
        sub_records = record[field.field_name]
        message_dict = self.fill_dependancy(message_dict, field.relation, sub_records)
        return message_dict

    @api.model
    def fill_dependancy(self, message_dict, model_name, records):
        if not message_dict['body']['dependency'].get(model_name):
            message_dict['body']['dependency'][model_name] = {}
        for sub_record in records:
            sub_record_id = str(sub_record.id)
            if not message_dict['body']['dependency'][model_name].get(sub_record_id):
                message_dict['body']['dependency'][model_name][sub_record_id] = {
                    'id': sub_record.id
                }
        return message_dict

    @api.model
    def fill_translation(self, message_dict, model, record_id, field, translations):
        if not message_dict['body']['root'][model][record_id].get('translation'):
            message_dict['body']['root'][model][record_id]['translation'] = {}
        if not message_dict['body']['root'][model][record_id]['translation'].get(field.map_name):
            message_dict['body']['root'][model][record_id]['translation'][field.map_name] = {}
            for translation in translations:
                message_dict['body']['root'][model][record_id]['translation'][field.map_name] = {}
                message_dict['body']['root'][model][record_id]['translation'][field.map_name][translation.lang] = {
                    'source': translation.source,
                    'value': translation.value
                }
        return message_dict

    def _generate_msg_body_deletion(self, exported_records, model_name):
        if model_name != 'bus.receive.transfer':
            raise exceptions.ValidationError(u"Deletion message not implemented for model : %s" % model_name)
        message_dict = {
            'body': {
                'root': {},
                'dependency': {},
            }
        }
        object_mapping = self.env['bus.object.mapping'].get_mapping(model_name)
        for record in exported_records:
            record_id = str(record.id)
            if not message_dict['body']['root'].get(model_name):
                message_dict['body']['root'][model_name] = {}
            message_dict['body']['root'][model_name][record_id] = {'id': record.id}
            if object_mapping.key_xml_id:
                ir_model_data = self.env['ir.model.data'].search([('model', '=', model_name),
                                                                  ('res_id', '=', record.id)])
                if ir_model_data:
                    message_dict['body']['root'][model_name][record_id].update({'xml_id': ir_model_data.complete_name})
            list_export_field = object_mapping.get_field_to_export()
            for field in list_export_field:
                field_name = field.field_id.name
                message_dict['body']['root'][model_name][record_id][field.map_name] = record[field_name]
                if record.model and record.local_id:
                    if not message_dict['body']['dependency'].get(record.model):
                        message_dict['body']['dependency'][record.model] = {}
                    if not message_dict['body']['dependency'][record.model].get(str(record.local_id)):
                        message_dict['body']['dependency'][record.model][str(record.local_id)] = {'id': record.local_id}
        return message_dict

    def _generate_check_msg_body(self, exported_records, model_name, dest):
        message_dict = {
            'body': {
                'root': {},
                'dependency': {},
            }
        }
        recipient = self.env['bus.base'].search([('bus_username', '=', dest)])
        for record in exported_records:
            record_id = str(record.id)
            check = self.get_check_transfer(model_name, record.id, recipient.id)
            check.write({
                'date_request': datetime.datetime.now(),
                'state': 'request'
            })
            if model_name not in message_dict['body']['root']:
                message_dict['body']['root'][model_name] = {}
            message_dict['body']['root'][model_name][record_id] = {'id': record.id, 'check_id': check.id}
        return message_dict

    # endregion

    @api.model
    def get_check_transfer(self, model_name, record_id, recipient_id):
        check = self.env['bus.check.transfer'].search([('res_model', '=', model_name), ('res_id', '=', record_id),
                                                       ('recipient_id', '=', recipient_id)], limit=1)
        if not check:
            check = self.env['bus.check.transfer'].create({'res_model': model_name, 'res_id': record_id,
                                                           'recipient_id': recipient_id})
        return check

    @api.model
    def send_synchro_return_message(self, parent_message_id, result):
        parent_message = self.env['bus.message'].browse(parent_message_id)
        message_dict = json.loads(parent_message.message)
        resp = collections.OrderedDict()
        log_message = u""
        return_state = 'done'
        for log in parent_message.log_ids:
            if log.type == 'error':
                return_state = 'error'
            log_message += u"%s : %s \n" % (log.type, log.information)
        log_message += u"Synchronization OK"

        dest = message_dict.get('header').get('origin')
        resp['header'] = message_dict.get('header')
        resp['header']['origin'] = message_dict.get('header').get('dest')
        resp['header']['serial_id'] = message_dict.get('header').get('serial_id', False)
        resp['header']['dest'] = dest
        resp['header']['treatment'] = 'SYNCHRONIZATION_RETURN'
        resp['header']['parent'] = message_dict.get('header').get('id')
        resp['body'] = {
            'dependency': {},
            'root': {},
        }
        resp['body']['return'] = {
            'result': result,
            'log': log_message,
            'state': return_state,
        }
        message = self.env['bus.message'].create_message(resp, 'sent', parent_message.configuration_id,
                                                         parent_message_id)
        message.send(resp)
        return message

    @api.model
    def send_dependancy_synchronization_demand(self, parent_message_id, demand):
        message = self.env['bus.message'].browse(parent_message_id)
        message_dict = json.loads(message.message)
        resp = collections.OrderedDict()
        destination = message_dict.get('header').get('origin')
        origin = message_dict.get('header').get('dest')
        resp['header'] = message_dict.get('header')
        resp['header']['origin'] = origin
        resp['header']['dest'] = destination
        resp['header']['treatment'] = 'DEPENDENCY_DEMAND_SYNCHRONIZATION'
        resp['body'] = {
            'dependency': {},
            'root': {},
            'demand': demand
        }
        new_msg = self.env['bus.message'].create_message(resp, 'sent', message.configuration_id, parent_message_id)
        new_msg.send(resp)
        return new_msg

    @api.model
    def send_dependency_synchronization_response(self, parent_message_id):
        message = self.env['bus.message'].browse(parent_message_id)
        message_dict = json.loads(message.message)
        resp = collections.OrderedDict()
        dest = message_dict.get('header').get('origin')
        origin = message_dict.get('header').get('dest')
        resp['header'] = message_dict.get('header')
        resp['header']['origin'] = origin
        resp['header']['dest'] = dest
        resp['header']['treatment'] = 'DEPENDENCY_SYNCHRONIZATION'
        resp['body'] = {
            'dependency': {},
            'root': {},
        }
        demand = message_dict.get('body', {}).get('demand', {})
        try:
            model_content, dependancy_content = self._generate_dependance_message(parent_message_id, demand)
            resp['body']['root'] = model_content
            resp['body']['dependency'] = dependancy_content
        except exceptions.ValidationError as validation_error:
            # Add message.log
            self.env['bus.message.log'].create({
                'message_id': parent_message_id,
                'type': 'error',
                'information': validation_error.value
            })
            return False

        resp['header'].pop('cross_id_origin_id')
        resp['header']['cross_id_origin_parent_id'] = message.cross_id_origin_id
        new_msg = self.env['bus.message'].create_message(resp, 'sent', message.configuration_id, parent_message_id)
        new_msg.send(resp)
        return True

    def _generate_dependance_message(self, message_id, demand):
        model_content = {}
        dependency_content = {}
        for model_name in demand.keys():
            record_ids = demand.get(model_name).keys()
            exported_records = self.env[model_name].search([('id', 'in', record_ids)])
            if len(exported_records) != len(record_ids):
                self.env['bus.message.log'].create({
                    'message_id': message_id,
                    'type': 'warning',
                    'information': u"All requested records not found : %s" % record_ids
                })
            result = self._generate_msg_body(exported_records, model_name)
            model_content[model_name] = result.get('body', {}).get('root', {}).get(model_name, {})
            for dep_model, dep_value in result.get('body', {}).get('dependency', {}).items():
                dependency_content.setdefault(dep_model, dependency_content.get(dep_model, {}))
                dependency_content[dep_model].update(dep_value)
        return model_content, dependency_content

    @api.model
    def send_deletion_return_message(self, message_id, return_message):
        message = self.env['bus.message'].browse(message_id)
        message_dict = json.loads(message.message)
        resp = collections.OrderedDict()
        dest = message_dict.get('header').get('origin')
        origin = message_dict.get('header').get('dest')
        resp['header'] = message_dict.get('header')
        resp['header']['origin'] = origin
        resp['header']['dest'] = dest
        resp['header']['treatment'] = 'DELETION_SYNCHRONIZATION_RETURN'
        resp['body'] = {
            'dependency': {},
            'root': {},
        }
        resp['body']['return'] = return_message
        message.send(resp)
        return True
