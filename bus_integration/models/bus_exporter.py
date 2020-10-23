# -*- coding: utf8 -*-

#  -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU Affero General Public License as
#     published by the Free Software Foundation, either version 3 of the
#     License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.
#
#     You should have received a copy of the GNU Affero General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

#
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
import uuid
import datetime
import collections
from openerp import models, api, exceptions
from openerp.tools import safe_eval
from openerp.addons.connector.session import ConnectorSession
from ..connector.jobs import job_generate_message


class BusSynchronizationExporter(models.AbstractModel):
    _name = 'bus.exporter'

    authorize_field_type = ['char', 'boolean', 'date', 'datetime', 'float', 'html', 'integer', 'text', 'selection', 'binary', ]

    # TODO :  a vérifier :  'binary', 'reference', 'serialized]

    @api.model
    def run_export(self, backend_bus_configuration_export_id, force_domain=False, jobify=True):
        """
        Create and send messages
        :param backend_bus_configuration_export_id: models to export with their conf
        :param force_domain
        :return: True or raise an exception
        """
        batch = self.env['bus.configuration.export'].browse(backend_bus_configuration_export_id)

        # last_send_date: limit the number models to synchronise, we only send models which have been updated after the
        #                 last export bus.configuration.export domain should be set to
        #                 [('write_date', '>', last_send_date)]
        export_domain = batch.domain and safe_eval(batch.domain, batch.export_domain_keywords()) or []

        active_test = True
        if batch.treatment_type not in ('BUS_SYNCHRONIZATION', 'RESTRICT_IDS_SYNCHRONIZATION'):
            object_mapping = self.env['bus.object.mapping'].search([('model_name', '=', batch.model)])
            if not object_mapping or not object_mapping.is_exportable:
                raise exceptions.ValidationError(u"Object mapping not configured for model : %s" % batch.model)

            if batch.treatment_type != 'DELETION_SYNCHRONIZATION' and object_mapping.deactivated_sync:
                active_test = False

        if force_domain:
            force_domain = safe_eval(force_domain, batch.export_domain_keywords())
            export_domain += force_domain

        message_list = []
        message_dict = {
            'header': {
                'origin': batch.configuration_id.sender_id.bus_username,
                'dest': batch.recipient_id.bus_username,
                'treatment': batch.treatment_type
            },
            'export': None
        }
        ids_to_export = self.with_context(active_test=active_test).env[batch.model].search(export_domain)
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

        msgs_group_uuid = "%s %s" % (str(uuid.uuid4()), batch.display_name)
        for export_msg in message_list:
            if jobify:
                job_generate_message.delay(ConnectorSession.from_env(self.env), self._name, batch.id, export_msg,
                                           msgs_group_uuid)
            else:
                job_generate_message(ConnectorSession.from_env(self.env), self._name, batch.id, export_msg,
                                     msgs_group_uuid)
        return msgs_group_uuid

    @api.model
    def generate_message(self, bus_configuration_export_id, export_msg, msgs_group_uuid):
        """ cron event or run batch btn click.. """
        batch = self.env['bus.configuration.export'].browse(bus_configuration_export_id)
        message_dict = collections.OrderedDict()
        message_dict['header'] = export_msg.get('header')
        message_dict['body'] = {
            'root': {},
            'dependency': {},
        }
        model_name = export_msg.get('export').get('model')
        ids = export_msg.get('export').get('ids')
        message_dict['header']['bus_configuration_export_id'] = batch.id
        active_test = True
        if batch.mapping_object_id.deactivated_sync:
            active_test = False
        exported_records = self.with_context(active_test=active_test).env[model_name].search([('id', 'in', ids)])
        if 'exported_to_bus_base_ids' in self.env[model_name]._fields.keys():
            for record in exported_records:
                base_ids = list(set(record.exported_to_bus_base_ids.ids + [batch.recipient_id.id]))
                record.sudo().write({'exported_to_bus_base_ids': [(6, 0, base_ids)]})
        message_type = message_dict.get('header').get('treatment')
        if message_type == 'DELETION_SYNCHRONIZATION':
            result = self._generate_msg_body_deletion(exported_records, model_name)
        elif message_type == 'CHECK_SYNCHRONIZATION':
            result = self._generate_check_msg_body(exported_records, model_name, message_dict['header']['dest'])
        elif message_type == 'BUS_SYNCHRONIZATION':
            result = self._generate_bus_synchronization_msg_body(exported_records)
        elif message_type == 'RESTRICT_IDS_SYNCHRONIZATION':
            result = {'body': {'root': {exported_records._name: exported_records.ids or [0]}}}
        elif message_type == 'SYNCHRONIZATION':
            result = self._generate_msg_body(exported_records, model_name)
        else:
            raise exceptions.except_orm("Message type '%s' unimplemented" % message_type)
        message_dict['body'] = result['body']

        message = self.env['bus.message'].create_message_from_batch(message_dict, batch,
                                                                    self.env.context.get('job_uuid', 'no_job'),
                                                                    msgs_group_uuid)

        if not ids and message_type not in ['RESTRICT_IDS_SYNCHRONIZATION']:
            message.add_log(u"no models to export")
            message.date_done = datetime.datetime.now()
            return

        send_msg_jobuuid = message.send(message_dict)
        if send_msg_jobuuid:
            message.add_log("message taken by job: %s" % send_msg_jobuuid)
        else:
            message.add_log(u"could not create send message job", 'error')

    # region def _generate_msg_body(self, exported_records, model_name):
    def _generate_bus_synchronization_msg_body(self, exported_records):
        message_dict = {'body': {'root': {exported_records._name: {}}}}
        for record in exported_records:
            record_id = str(record.id)
            message_dict['body']['root'][record._name].setdefault(record_id, {})
            message_dict['body']['root'][record._name][record_id]['write_date'] = record.write_date
            message_dict['body']['root'][record._name][record_id]['display_name'] = record.display_name or ""
        return message_dict

    def _generate_msg_body(self, exported_records, model_name):
        """
        :param exported_records: recordset
        :param model_name: 'model.name'
        :return: the dictionary for message 'body'
        """
        message_dict = {
            'body': {
                'root': {},
                'dependency': {},
                'post_dependency': {},
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
            list_export_field = object_mapping.get_field_to_export()  # list of field.object.mapping
            for field in list_export_field:
                if field.type_field == 'many2many':
                    message_dict = self.fill_many2many(message_dict, record, field)
                elif field.type_field == 'one2many':
                    message_dict = self.fill_one2many(message_dict, record, field)
                elif field.type_field == 'many2one':
                    message_dict = self.fill_many2one(message_dict, record, field)
                elif field.type_field in self.authorize_field_type:
                    message_dict = self.fill_field(message_dict, record, field)
            message_dict['body']['root'][record._name][record_id]['write_date'] = record.write_date
            message_dict['body']['root'][record._name][record_id]['display_name'] = record.display_name or ""
        return message_dict

    @api.model
    def get_xml_id(self, model, record_id):
        ir_model_data = self.env['ir.model.data'].search([('model', '=', model), ('res_id', '=', record_id)], limit=1,
                                                         order='id ASC')
        return ir_model_data and ir_model_data.complete_name or False

    @api.model
    def fill_field(self, message_dict, record, field):
        record_id = str(record.id)
        message_dict['body']['root'][record._name][record_id][field.map_name] = record[field.field_name]
        if field.field_id.ttype == 'char' and field.field_id.translate:
            if field.field_name in record._inherit_fields:
                parent_model, link_field, _, _ = record._inherit_fields[field.field_name]
                model = parent_model
                res_id = record[link_field].id
            else:
                model = record._name
                res_id = record.id
            # makes sure all fields are translated. before export.
            # Actually if the translation form has never been opened ir_translation records are not create
            self.env['ir.translation'].translate_fields(model, res_id, field=field.field_name)
            translation_name = "%s,%s" % (model, field.field_name)
            translations = self.env['ir.translation'].search([('name', '=', translation_name),
                                                              ('res_id', '=', res_id)])
            if translations:
                message_dict = self.fill_translation(message_dict, record._name, record_id, field, translations)
        return message_dict

    @api.model
    def fill_many2one(self, message_dict, record, field):
        record_id = str(record.id)
        if not record[field.field_name].id:
            message_dict['body']['root'][record._name][record_id][field.map_name] = False
            return message_dict
        message_dict['body']['root'][record._name][record_id][field.map_name] = {
            'id': record[field.field_name].id,
            'model': field.field_id.relation,
            'type_field': 'many2one'
        }
        sub_record = record[field.field_name]
        message_dict = self.fill_dependency(message_dict, field, sub_record)
        return message_dict

    @api.model
    def fill_many2many(self, message_dict, record, field):
        """ many2many field """
        record_id = str(record.id)
        message_dict['body']['root'][record._name][record_id][field.map_name] = {
            'ids': record[field.field_name].ids,
            'model': field.field_id.relation,
            'type_field': field.type_field
        }
        sub_records = record[field.field_name]
        message_dict = self.fill_dependency(message_dict, field, sub_records)
        return message_dict

    @api.model
    def fill_one2many(self, message_dict, record, field):
        """ one2many field
            We do not send ids, we send them as post_dependancyrequest
            in receiver base, existing ids will be kept when present in post_dependency, otherwise, ids will
            be added by the ORM when the missing objects will be synchronized from the post-dependency synchronisation
            request that will be issued after receiver object's creation
        """
        record_id = str(record.id)
        message_dict['body']['root'][record._name][record_id][field.map_name] = {
            'ids': [],
            'model': field.field_id.relation,
            'type_field': field.type_field
        }
        sub_records = record[field.field_name]
        message_dict = self.fill_post_dependency(message_dict, field, sub_records)
        return message_dict

    @api.model
    def fill_dependency(self, message_dict, field, records):
        return self.fill_any_dependency('dependency', message_dict, field, records)

    @api.model
    def fill_post_dependency(self, message_dict, field, records):
        message_dict['body'].setdefault('post_dependency', {})
        return self.fill_any_dependency('post_dependency', message_dict, field, records)

    @api.model
    def fill_any_dependency(self, dependency_type, message_dict, field, records):
        model_name = field.field_id.relation
        if not message_dict['body'].get(dependency_type, {}).get(model_name):
            message_dict['body'][dependency_type][model_name] = {}
        for sub_record in records:
            sub_record_id = str(sub_record.id)
            if not message_dict['body'][dependency_type][model_name].get(sub_record_id):
                message_dict['body'][dependency_type][model_name][sub_record_id] = {}
        return message_dict

    @api.model
    def fill_translation(self, message_dict, model, record_id, field, translations):
        if not message_dict['body']['root'][model][record_id].get('translation'):
            message_dict['body']['root'][model][record_id]['translation'] = {}
        if not message_dict['body']['root'][model][record_id]['translation'].get(field.map_name):
            message_dict['body']['root'][model][record_id]['translation'][field.map_name] = {}
            for translation in translations:
                message_dict['body']['root'][model][record_id]['translation'][field.map_name][translation.lang] = {
                    'src': translation.src,
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
            check.write({'date_request': datetime.datetime.now(), 'state': 'request'})
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
        resp['header']['dest'] = dest
        resp['header']['treatment'] = 'SYNCHRONIZATION_RETURN'
        resp['header']['parent'] = message_dict.get('header').get('id')
        resp['body'] = {
            'dependency': {},
            'post_dependency': {},
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
    def send_post_dependancy_synchronization_demand(self, parent_message_id, demand):
        message = self.env['bus.message'].browse(parent_message_id)
        message_dict = json.loads(message.message)
        resp = collections.OrderedDict()
        destination = message_dict.get('header').get('origin')
        origin = message_dict.get('header').get('dest')
        resp['header'] = message_dict.get('header')
        resp['header']['origin'] = origin
        resp['header']['dest'] = destination
        resp['header']['message_parent_id'] = False
        resp['header']['cross_id_origin_parent_id'] = False
        resp['header']['treatment'] = 'POST_DEPENDENCY_DEMAND_SYNCHRONIZATION'
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
        demand, message, resp = self._prepare_dependency_synchro_response(parent_message_id)
        try:
            model_content, dependancy_content, post_dep_content = self._generate_dependance_message(message, demand)
            resp['body']['root'] = model_content
            resp['body']['dependency'] = dependancy_content
            resp['body']['post_dependency'] = post_dep_content
        except exceptions.ValidationError as validation_error:
            message.add_log(validation_error.value, 'error')
            return False

        resp['header'].pop('cross_id_origin_id')
        resp['header']['cross_id_origin_parent_id'] = message.cross_id_origin_id
        new_msg = self.env['bus.message'].create_message(resp, 'sent', message.configuration_id, parent_message_id)
        new_msg.send(resp)
        return True

    @api.model
    def send_post_dependency_synchronization_response(self, parent_message_id):
        demand, message, resp = self._prepare_dependency_synchro_response(parent_message_id)
        try:
            model_content, dependancy_content, post_dep_content = self._generate_dependance_message(message, demand)
            resp['body']['root'] = model_content
            resp['body']['dependency'] = dependancy_content
            resp['body']['post_dependency'] = post_dep_content
        except exceptions.ValidationError as validation_error:
            message.add_log(validation_error.value, 'error')
            return False

        resp['header'].pop('cross_id_origin_parent_id')  # we need the responde msg to have no cross_id_origin_parent_id
        # so the parent message (synchro message that triggered the post-dep request) will not be processed again
        new_msg = self.env['bus.message'].create_message(resp, 'sent', message.configuration_id, parent_message_id)
        new_msg.send(resp)
        return True

    def _prepare_dependency_synchro_response(self, parent_message_id):
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
        return demand, message, resp

    def _generate_dependance_message(self, message, demand):
        model_content = {}
        dependency_content = {}
        post_dependency_content = {}
        # TODO:  Envoyer les logs au bus pour permettre de les identifiers directement dans le bus
        for model_name in demand.keys():
            record_ids = demand.get(model_name).keys()
            domain = [('id', 'in', record_ids)]
            mapping = self.env['bus.object.mapping'].search([('model_name', '=', model_name)])
            if mapping.deactivated_sync:
                domain += ['|', ('active', '=', False), ('active', '=', True)]
            exported_records = self.env[model_name].search(domain)
            if exported_records.ids != record_ids:
                if not record_ids:
                    log = u"Model %s - No records found : %s [%s]" % (model_name, record_ids, exported_records.ids)
                    message.add_log(log, 'error')
                else:
                    log = u"All requested records not found : %s - %s" % (model_name, record_ids)
                    message.add_log(log, 'warning')
            result = self._generate_msg_body(exported_records, model_name)
            model_content[model_name] = result.get('body', {}).get('root', {}).get(model_name, {})
            for dep_model, dep_value in result.get('body', {}).get('dependency', {}).items():
                dependency_content.setdefault(dep_model, dependency_content.get(dep_model, {}))
                dependency_content[dep_model].update(dep_value)
            for post_dep_model, post_dep_value in result.get('body', {}).get('post_dependency', {}).items():
                post_dependency_content.setdefault(post_dep_model, post_dependency_content.get(post_dep_model, {}))
                post_dependency_content[post_dep_model].update(post_dep_value)
        return model_content, dependency_content, post_dependency_content

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

    @api.model
    def send_restrict_id_response(self, parent_message, result_dict):
        message_dict = json.loads(parent_message.message)

        log_message = u""
        return_state = 'done'
        for log in parent_message.log_ids:
            if log.type == 'error':
                return_state = 'error'
            log_message += u"%s : %s \n" % (log.type, log.information)

        dest = message_dict.get('header').get('origin')

        resp = collections.OrderedDict()
        resp['header'] = message_dict.get('header')
        resp['header']['origin'] = message_dict.get('header').get('dest')
        resp['header']['dest'] = dest
        resp['header']['treatment'] = 'RESTRICT_IDS_SYNCHRONIZATION_RETURN'
        resp['header']['parent'] = message_dict.get('header').get('id')
        resp['body'] = {
            'dependency': {},
            'root': {},
        }
        resp['body']['return'] = {
            'result': result_dict,
            'log': log_message,
            'state': return_state,
        }
        message = self.env['bus.message'].create_message(resp, 'sent', parent_message.configuration_id,
                                                         parent_message.id)
        message.send(resp)
        return message
