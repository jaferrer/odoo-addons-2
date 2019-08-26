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
from datetime import datetime

from psycopg2._psycopg import IntegrityError

from openerp import models, api, exceptions


class BusSynchronizationImporter(models.AbstractModel):
    _name = 'bus.importer'

    @api.model
    def import_synchronization_message(self, message_id):
        import_results = {}
        message = self.env['bus.message'].browse(message_id)
        message_dict = json.loads(message.message, encoding='utf-8')
        root = message_dict.get('body', {}).get('root', {})
        dependencies = message_dict.get('body', {}).get('dependency', {})
        demand = self.check_needed_dependencies(message, dependencies)
        if not demand:
            for model in root.keys():
                import_results[model] = {}
                for record in root.get(model).values():
                    original_id = record.get('id', False)
                    external_key = record.get('external_key', False)
                    result = self.run_import(message_id, record, model, dependencies)
                    if not result:
                        error_log = self.get_syncrhonization_errors(message_id, model, original_id)
                        result = {
                            'id': False,
                            'external_key': external_key,
                            'result': result,
                            'error': error_log,
                            'bus_original_id': original_id
                        }
                    else:
                        result.update({'bus_original_id': original_id})
                    import_results[model][original_id] = result
        return import_results, demand

    @api.model
    def get_syncrhonization_errors(self, message_id, model, original_id):
        message_logs = self.env['bus.message.log'].search([('message_id', '=', message_id), ('model', '=', model),
                                                           ('sender_record_id', '=', original_id)])
        nb_log = 0
        error_log = {}
        for log in message_logs:
            error_log[nb_log] = {'message_id': message_id,
                                 'type': log.type,
                                 'information': log.information,
                                 'model': log.model,
                                 'sender_record_id': log.sender_record_id,
                                 'external_key': log.external_key}
            nb_log = nb_log + 1
        return error_log

    @api.model
    def import_deletion_synchronization_message(self, message_id):
        message = self.env['bus.message'].browse(message_id)
        message_dict = json.loads(message.message, encoding='utf-8')
        root = message_dict.get('body', {}).get('root', {})
        dependencies = message_dict.get('body', {}).get('dependency', {})
        result = {}
        for model in root.keys():
            result[model] = {}
            for record in root.get(model).values():
                unlink = self.run_import_deletion(record, model, dependencies)
                result[model][record.get('id')] = {
                    'unlink': unlink,
                    'external_key': record.get('external_key'),
                    'id': record.get('id')
                }
        return result

    def check_needed_dependencies(self, message, dependencies):
        demand = {}
        for model in dependencies.keys():
            for record in dependencies.get(model).values():
                needed = self.check_needed_dependency(record, model)
                if needed:
                    needed_model = needed.get('model', '')
                    if needed_model not in demand:
                        demand[needed_model] = {}
                    str_id = str(record.get('id'))
                    demand[needed_model][str_id] = {
                        'external_key': needed.get('external_key'),
                        'id': str_id,
                    }
                    log = message.add_log(u"Record needed", 'info')
                    log.write({'sender_record_id': str_id,
                               'model': needed_model
                               })
        return demand

    def check_needed_dependency(self, record, model):
        external_key = record.get('external_key', False)
        _, odoo_record = self.env['bus.binder'].get_record_by_external_key(external_key, model)
        if not odoo_record:
            return {'model': model, 'external_key': external_key, 'id': record.get('id', False)}
        return {}

    @api.model
    def get_records_for_dependency(self, record, obj, dependencies):
        needed_dependencies = []
        datas = record.get(obj)
        model = datas.get('model')
        if 'ids' in datas:
            for id in datas.get('ids'):
                if model in dependencies and str(id) in dependencies.get(model):
                    needed_dependencies.append(dependencies.get(model).get(str(id)))
        elif model in dependencies and str(datas.get('id')) in dependencies.get(model):
            needed_dependencies.append(dependencies.get(model).get(str(datas.get('id'))))
        return needed_dependencies

    @api.model
    def _import_dependencies(self, record, dependencies):
        # TODO : A vérifier
        for obj in record.keys():
            if isinstance(record.get(obj), dict) and obj not in ["_dependency", "_bus_model"]:
                needed_dependencies = self.get_records_for_dependency(record, obj)
                for needed in needed_dependencies:
                    depend = self.run_import(needed, record.get(obj).get('model'), dependencies)
                    if depend:
                        return True
        return False

    @api.model
    def _get_object_mapping(self, model):
        return self.env['bus.object.mapping'].search([('model_name', '=', model), ('active', '=', True),
                                                      ('is_importable', '=', True)])

    def _update_translation(self, transfer, translation, ir_translation_name, lang):
        ir_translation = self.env['ir.translation'].search([('name', '=', ir_translation_name),
                                                            ('type', '=', 'model'), ('lang', '=', lang),
                                                            ('res_id', '=', transfer.local_id)])
        translation.update({'comments': u"Set by BUS %s" % datetime.now()})
        if ir_translation:
            ir_translation.write(translation)
        else:
            translation.update({
                'name': ir_translation_name,
                'lang': lang,
                'res_id': transfer.local_id,
                'type': 'model'
            })
            self.env['ir.translation'].create(translation)

    @api.model
    def _update_translations(self, transfer, translations):
        """
        translate the model in the bus message to the subscriber language
        :param transfer:
        :param translations:
        :return: warnings if any or []. translations errors are not critical.
        """
        warnings = []
        for field in translations:
            for lang in translations.get(field):
                ir_translation_name = "%s,%s" % (transfer.model, field)
                if not self.env['res.lang'].search([('code', '=', lang)]):
                    warnings .append(('warning', 'could not translate %s. lang %s is not installed' %
                                      (ir_translation_name, lang)))
                else:
                    translation = translations.get(field).get(lang, "")
                    self._update_translation(transfer, translation, ir_translation_name, lang)
        return warnings

    @api.model
    def run_import(self, message_id, record, model, dependencies):
        external_key = record.pop('external_key')
        translation = record.pop('translation', False)
        record_id = record.get('id')
        xml_id = record.pop('xml_id', False)
        model_mapping = self._get_object_mapping(model)
        if not model_mapping:
            message = self.env['bus.message'].browse(message_id)
            log = message.add_log(u"Model %s not configured for import!" % model, 'error')
            log.write({
                'model': model,
                'sender_record_id': record_id,
                'external_key': external_key
            })
            return False

        errors = []
        transfer = False
        try:
            with self.env.cr.savepoint():
                transfer, odoo_record = self.env['bus.binder']\
                    .process_binding(record, model, external_key, model_mapping, dependencies, xml_id)
                binding_data, record_data, errors = self.env['bus.mapper'] \
                    .process_mapping(record, model, external_key, model_mapping, dependencies, odoo_record)
                if len(odoo_record) > 1:
                    errors.append(('error', u"Too many record find for %s : %s" % (model, record_id)))
        except IntegrityError as err:
            fields_mapping = self.env['bus.object.mapping.field'].search([('is_migration_key', '=', True),
                                                                          ('mapping_id', '=', model_mapping.id)])
            fields_name = str([field.field_name for field in fields_mapping])
            errors.append(('error', u"invalid migration_key on %s. multiple records found with migration_key %s, "
                                    u"detail: %s" % (fields_name, model, err)))
        critical_error = [error for error in errors if error[0] == 'error']
        if not critical_error:
            try:
                with self.env.cr.savepoint():
                    transfer, odoo_record, error_tuple = transfer \
                        .import_datas(transfer, odoo_record, binding_data, record_data)
                    if error_tuple:
                        errors.append(error_tuple)
                    if translation:
                        self._update_translations(transfer, translation)
            except (exceptions.ValidationError, exceptions.except_orm, IntegrityError) as err:
                msg = u"Unable to import record model: %s id: %s, external_key: %s, " \
                      u"detail: %s" % (model, record_id, external_key, err.__str__().decode('utf-8'))
                errors.append(('error', msg))
        has_critical_error = self.register_errors(errors, message_id, model, record.get('id', False), external_key)
        if not transfer or has_critical_error:
            return False

        return {'external_key': external_key, 'id': transfer.local_id}

    @api.model
    def register_errors(self, errors, message_id, model, record_id, external_key):
        has_error = False
        for error in errors:
            error_type, error_message = error
            if error_type == 'error':
                has_error = True
            message = self.env['bus.message'].browse(message_id)
            log = message.add_log(error_message, error_type)
            log.write({
                'model': model,
                'sender_record_id': record_id,
                'external_key': external_key
            })
        return has_error

    @api.model
    def run_import_deletion(self, record, model, dependencies):
        unlink = False
        model_to_delete = record.get('model', False)
        id_to_delete = record.get('local_id', False)
        external_key_to_delete = dependencies.get(model_to_delete, {}).get(str(id_to_delete), {}).get('external_key',
                                                                                                      False)
        if external_key_to_delete and record.get('to_deactivate', False):
            binding_to_delete = self.env[model].search([('model', '=', model_to_delete),
                                                        ('external_key', '=', external_key_to_delete)])
            if binding_to_delete:
                record_to_delete = self.env[model_to_delete].browse(binding_to_delete.local_id)
                if record_to_delete:
                    if 'active' in record_to_delete._fields:
                        record_to_delete.write({'active': False})
                        unlink = "Ok"
                        binding_to_delete.write({'to_deactivate': False})
                    else:
                        try:
                            record_to_delete.unlink()
                            unlink = "Ok"
                            binding_to_delete.write({'to_deactivate': False})
                        except exceptions.except_orm:
                            unlink = False
        return unlink

    @api.model
    def register_synchro_deletion_return(self, message_id):
        message = self.env['bus.message'].browse(message_id)
        message_dict = json.loads(message.message, encoding='utf-8')
        result = message_dict.get('body', {}).get('return', {})
        for model in result.keys():
            for id in result.get(model).keys():
                datas = result.get(model).get(id)
                transfer = self.env[model].browse(datas.get('id'))
                if transfer:
                    transfer.write({
                        'received_data': json.dumps(datas, indent=4),
                        'external_key': datas.get('external_key')
                    })
        return True

    @api.model
    def register_synchro_check_return(self, message_id):
        message = self.env['bus.message'].browse(message_id)
        message_dict = json.loads(message.message, encoding='utf-8')
        result = message_dict.get('body', {}).get('root', {})
        for model in result.keys():
            for id in result.get(model).keys():
                datas = result.get(model).get(id)
                check = self.env['bus.check.transfer'].browse(datas.get('check_id'))
                if check and check.res_model == model and check.res_id == int(id):
                    state = 'not_find'
                    if datas.get('recipient_record_id'):
                        state = 'find'
                    check.write({
                        'recipient_record_id': datas.get('recipient_record_id', False),
                        'external_key': datas.get('external_key', False),
                        'state': state,
                        'date_response': datetime.now()
                    })
                if not check:
                    error = u"Check not find : %s - %s(%s)" % (datas.get('check_id', False), model, id)
                    log = message.add_log(error, 'error')
                    log.sender_record_id = id
        return True

    @api.model
    def import_bus_references(self, message_id, dict_result, return_state):
        if not dict_result:
            return True
        for model in dict_result.keys():
            for id in dict_result.get(model).keys():
                datas = dict_result.get(model).get(id)
                external_key = datas.get('external_key', False)
                errors = datas.get('error', False)
                msg_error = ""
                if errors:
                    for error in errors.values():
                        msg_error += error.get('information', "")
                        msg_error += u"\n"
                self.create_receive_transfer(model, external_key, id, datas, msg_error)
                if return_state == 'error':
                    self.create_error_synchronization(message_id, model, id, external_key, datas)

    @api.model
    def create_receive_transfer(self, model, external_key, local_id, datas, msg_error):
        transfer = self.env['bus.binder']._get_transfer(external_key, model)
        if not transfer:
            self.env['bus.receive.transfer'].create({
                'model': model,
                'local_id': local_id,
                'external_key': external_key,
                'received_data': json.dumps(datas, indent=4),
                'msg_error': msg_error
            })
        else:
            transfer.write({'msg_error': msg_error})

    @api.model
    def create_error_synchronization(self, message_id, model, local_id, external_key, datas):
        message = self.env['bus.message'].browse(message_id)
        dict_message = json.loads(message.message)
        origin = dict_message.get('header', {}).get('origin', False)
        dest = dict_message.get('header', {}).get('dest', False)
        recipient = False
        sender = False
        if origin:
            recipient = self.env['bus.base'].search([('bus_username', '=', origin)])
        if dest:
            sender = self.env['bus.base'].search([('bus_username', '=', dest)])
        for error in datas.get('error', {}).values():
            message = self.env['bus.message'].browse(message_id)
            log = message.add_log(error.get('information', ''), error.get('type', ''))
            log.write({
                'model': model,
                'sender_record_id': local_id,
                'external_key': external_key,
                'recipient_id': recipient and recipient.id or False,
                'sender_id': sender and sender.id or False,
            })
