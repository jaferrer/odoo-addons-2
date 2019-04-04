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
from openerp import models, api


class BusSynchronizationImporter(models.AbstractModel):
    _name = 'bus.importer'

    @api.model
    def import_synchronization_message(self, message_id):
        import_results = {}
        message = self.env['bus.message'].browse(message_id)
        message_dict = json.loads(message.message, encoding='utf-8')
        root = message_dict.get('body', {}).get('root', {})
        dependencies = message_dict.get('body', {}).get('dependency', {})
        demand = self.check_needed_dependencies(message_id, dependencies)
        if not demand:
            for model in root.keys():
                import_results[model] = {}
                for record in root.get(model).values():
                    result = self.run_import(message_id, record, model, dependencies)
                    original_id = record.get('id', False)
                    result.update({'bus_original_id': original_id})
                    import_results[model][original_id] = result
        return import_results, demand

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

    def check_needed_dependencies(self, message_id, dependencies):
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
                    self.env['bus.message.log'].create({
                        'message_id': message_id,
                        'log': 'info',
                        'information': u"Need record id : %s model : %s" % (str_id, needed_model)
                    })
        return demand

    def check_needed_dependency(self, record, model):
        external_key = record.get('external_key', False)
        record.get('external_key', False)
        transfer, odoo_record = self.env['bus.binder'].get_record_by_external_key(external_key, model)
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

    @api.model
    def _update_translation(self, transfer, translations):
        for field in translations:
            for lang in translations.get(field):
                translation = translations.get(field).get(lang, "")
                ir_translation_name = "%s,%s" % (transfer.model, field)
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
    def run_import(self, message_id, record, model, dependencies):
        external_key = record.pop('external_key')
        translation = record.pop('translation', False)
        # remote_id = record.pop('id')
        xml_id = record.pop('xml_id', False)
        model_mapping = self._get_object_mapping(model)
        if not model_mapping:
            self.env['bus.message.log'].create({
                'message_id': message_id,
                'type': 'error',
                'information': u"Model %s not configured for import!" % model
            })
            return False
        binding = self.env['bus.binder'].process_binding(external_key, model, record, xml_id,
                                                         model_mapping, dependencies)
        transfer, odoo_record = binding
        mapping = self.env['bus.mapper'].process_mapping(record, model, external_key, model_mapping,
                                                         dependencies)
        binding_data, record_data, errors = mapping
        no_error = True
        for error in errors:
            error_type, error_message = error
            if error_type == 'error':
                no_error = False
            self.env['bus.message.log'].create({
                'message_id': message_id,
                'type': error_type,
                'information': error_message
            })
        if no_error:
            transfer, odoo_record = transfer.import_datas(transfer, odoo_record, binding_data, record_data)
            if translation:
                self._update_translation(transfer, translation)
            return {'external_key': external_key, 'id': transfer.local_id}
        return False

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
                    record_to_delete.write({'active': False})
                    unlink = "Ok"
                binding_to_delete.write({'to_deactivate': False})
            else:
                unlink = 'null'
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
                        'received_data': datas,
                        'external_key': datas.get('external_key')
                    })
        return True

    @api.model
    def import_bus_references(self, dict_result):
        if not dict_result:
            return True
        for model in dict_result.keys():
            for id in dict_result.get(model).keys():
                datas = dict_result.get(model).get(id)
                external_key = datas.get('external_key', False)
                local_id = datas.get('bus_original_id', False)
                transfer = self.env['bus.binder']._get_transfer(external_key, model)
                if not transfer:
                    self.env['bus.receive.transfer'].create({
                        'model': model,
                        'local_id': local_id,
                        'external_key': external_key,
                        'received_data': datas
                    })
