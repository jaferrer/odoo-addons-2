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
from datetime import datetime

from psycopg2._psycopg import IntegrityError

from openerp import models, api, exceptions


class BusSynchronizationImporter(models.AbstractModel):
    _name = 'bus.importer'

    @api.model
    def import_synchronization_message(self, message_id):
        """
        1) check if dependency are needed (from the id listed in the dependency key of the message,
           check in bus.binder if the id is synchronized)
        2) if yes, return the list of id needed
        3) if no, create/update the record and return the post dependencies to complete the one2many fields
        """
        import_results = {}
        post_demand = {}
        message = self.env['bus.message'].browse(message_id)
        message_dict = json.loads(message.message, encoding='utf-8')
        root = message_dict.get('body', {}).get('root', {})
        demand = self.check_needed_dependencies(message)
        if not demand:
            for model in root.keys():
                import_results[model] = {}
                records_dict = root.get(model)
                ordered_record_keys = sorted(records_dict, key=lambda k: records_dict[k]['write_date'])
                for key in ordered_record_keys:
                    record = records_dict[key]
                    original_id = record.get('id', False)
                    external_key = record.get('external_key', False)
                    result = self.run_import(message, record, model)
                    if not result:
                        error_log = self.get_synchronization_errors(message_id, model, original_id)
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
            post_demand = self.check_needed_post_dependencies(message)
        return import_results, demand, post_demand

    @api.model
    def get_synchronization_errors(self, message_id, model, original_id):
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

    def check_needed_dependencies(self, message):
        dependencies = message.get_json_dependencies()
        return self.check_for_dependencies(dependencies, message)

    def check_needed_post_dependencies(self, message):
        post_dependencies = message.get_json_post_dependencies()
        return self.check_for_dependencies(post_dependencies, message, with_log=False)

    def check_for_dependencies(self, dependencies, message, demand=None, with_log=True):
        demand = demand if demand else {}
        for model in dependencies.keys():
            for record_id in dependencies[model].keys():
                needed = self.check_needed_dependency(dependencies[model][record_id], model)
                if needed:
                    needed_model = needed.get('model', '')
                    if needed_model not in demand:
                        demand[needed_model] = {}
                    demand[needed_model][record_id] = {'external_key': needed.get('external_key')}
                    if with_log:
                        log = message.add_log(u"Record needed", 'info')
                        log.write({'sender_record_id': record_id, 'model': needed_model})
        return demand

    def check_needed_dependency(self, record, model):
        # no dependance required if transform_rule is applied by the bus. bus_recipient_id is the local id
        if "transform_rule" in record:
            return {}

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
    def _get_object_mapping(self, model):
        return self.env['bus.object.mapping'].search([('model_name', '=', model), ('active', '=', True),
                                                      ('is_importable', '=', True)])

    def _update_translation(self, record_id, translation, ir_translation_name, lang):
        ir_translation = self.env['ir.translation'].search([('name', '=', ir_translation_name),
                                                            ('type', '=', 'model'), ('lang', '=', lang),
                                                            ('res_id', '=', record_id)])
        translation.update({'comments': u"Set by BUS %s" % datetime.now()})
        if ir_translation:
            ir_translation.write(translation)
        else:
            translation.update({
                'name': ir_translation_name,
                'lang': lang,
                'res_id': record_id,
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
        record = self.env[transfer.model].search([('id', '=', transfer.local_id)])
        if not record:
            warnings.append(('error', 'Translation on %s not applicable, record %s not found' %
                                      (transfer.model, transfer.local_id)))
            return warnings
        for field in translations:
            for lang in translations.get(field):
                if field in self.env[transfer.model]._inherit_fields:
                    parent_model, link_field, _, _ = record._inherit_fields[field]
                    model = parent_model
                    record_id = record[link_field].id
                else:
                    model = record._name
                    record_id = record.id
                ir_translation_name = "%s,%s" % (model, field)
                if not self.env['res.lang'].search([('code', '=', lang)]):
                    warnings .append(('warning', 'could not translate %s. lang %s is not installed' %
                                      (ir_translation_name, lang)))
                else:
                    translation = translations.get(field).get(lang, "")
                    self._update_translation(record_id, translation, ir_translation_name, lang)
        return warnings

    @api.model
    def run_import(self, message, record, model):
        """
        :param message: a bus.message object
        :param record: dictionary containing the fields : value for one record
        :param model: 'model.model'
        :return False if error, {'external_key': external_key, 'id': local_id}
        """
        external_key = record.pop('external_key')
        translation = record.pop('translation', False)
        record_id = record.get('id')
        xml_id = record.pop('xml_id', False)
        model_mapping = self._get_object_mapping(model)
        if not model_mapping:
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
                transfer, odoo_record, errors = self.env['bus.binder']\
                    .process_binding(record, model, external_key, model_mapping, message, xml_id)
                if not errors:
                    binding_data, record_data, errors = self.env['bus.mapper'] \
                        .process_mapping(record, model, external_key, model_mapping, message, odoo_record)
        except IntegrityError as err:
            errors.append(('error', err))
        critical_error = [error for error in errors if error[0] == 'error']
        if not critical_error:
            try:
                with self.env.cr.savepoint():
                    transfer, odoo_record, error_tuple = transfer \
                        .import_datas(transfer, odoo_record, binding_data, record_data, message)
                    if error_tuple:
                        errors.append(error_tuple)
                    if translation:
                        self._update_translations(transfer, translation)
            except (exceptions.ValidationError, exceptions.except_orm, IntegrityError) as err:
                msg = u"Unable to import record model: %s id: %s, external_key: %s, " \
                      u"detail: %s" % (model, record_id, external_key, err.__str__().decode('utf-8'))
                errors.append(('error', msg))
        has_critical_error = self.register_errors(errors, message.id, model, record.get('id', False), external_key)
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
    def run_synchro_restrict_ids(self, message):
        """
        inactive synchronized records not in ids if active field is present or delete them
        """
        message_dict = json\
            .loads(message.message, encoding='utf-8')\
            .get('body', {})\
            .get('root', {})

        return_dict = {}
        for model in message_dict.keys():
            return_dict[model] = {}
            if not self.env[model]._fields.get('active'):
                error = "%s has no 'active' field. restrict id by deletion not implemented" % model
                message.add_log(error, 'error')
                return_dict[model]['error'] = error
            else:
                ids_to_keep = message_dict[model]
                receive_transfer_to_delete = self.env['bus.receive.transfer'].search([
                    ('model', '=', model),
                    ('local_id', 'not in', ids_to_keep)
                ])
                ids_to_inactive = receive_transfer_to_delete.mapped('local_id')
                records = self.env[model].browse(ids_to_inactive)
                records.write({'active': False})
                return_dict[model]['inactivated'] = records.ids
        return return_dict

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
    def register_synchro_bus_response(self, message):
        message_dict = json.loads(message.message, encoding='utf-8')
        result = message_dict.get('body', {}).get('return', {}).get('result', {})
        for model in result.keys():
            for id in result[model].keys():
                external_key = result[model][id]
                self.create_receive_transfer(message, model, external_key, id, False, False)
        return True

    @api.model
    def register_synchro_restrict_ids_return(self, message):
        message_dict = json.loads(message.message, encoding='utf-8')
        result = message_dict.get('body', {}).get('return', {}).get('state', 'error')
        return result == 'done'

    @api.model
    def import_bus_references(self, message, dict_result, return_state):
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
                self.create_receive_transfer(message, model, external_key, id, datas, msg_error)
                if return_state == 'error':
                    self.create_error_synchronization(message.id, model, id, external_key, datas)

    @api.model
    def create_receive_transfer(self, message, model, external_key, local_id, datas, msg_error):
        transfer = self.env['bus.binder']._get_transfer(external_key, model)
        if not transfer:
            self.env['bus.receive.transfer'].create({
                'model': model,
                'local_id': local_id,
                'external_key': external_key,
                'received_data': json.dumps(datas, indent=4),
                'msg_error': msg_error,
                'origin_base_id': message.get_base_origin().id,
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
