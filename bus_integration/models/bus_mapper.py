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

from openerp import models, api


class BusSynchronizationMapper(models.AbstractModel):
    _name = 'bus.mapper'

    @api.model
    def process_mapping(self, record, record_model, external_key, model_mapping, dependencies):
        error = []
        binding_data = {
            'model': record_model,
            'external_key': external_key,
            'received_data': record,
        }
        record_data = {}
        all_importable_field = [field.map_name for field in model_mapping.field_ids if field.import_field]
        required_fields = [field.map_name for field in model_mapping.field_ids if
                           field.field_id.required and field.import_field]
        all_importable_field.append('xml_id')
        all_importable_field.append('id')
        all_importable_field.append('translation')
        all_importable_field.append('external_key')
        for field_key in record.keys():
            if field_key not in all_importable_field:
                error.append(('warning', u"Error field %s not configured for import" % field_key))
            elif field_key in required_fields and not record.get(field_key):
                error.append(('error', u"Error field %s is required, record id : %s" % (field_key, record.get('id'))))
            else:
                if isinstance(record.get(field_key), dict):
                    relational_values = False
                    model = record.get(field_key).get('model')
                    type_field = record.get(field_key).get('type_field')
                    if type_field == 'many2one':
                        needed_id = record.get(field_key).get('id')
                        relational_values = self.get_relational_value(model, needed_id, dependencies)
                    if type_field == 'many2many':
                        needed_ids = record.get(field_key).get('ids')
                        relational_values = [(6, False, self.get_multiple_relational_value(model, needed_ids,
                                                                                           dependencies))]
                    record_data[field_key] = relational_values
                else:
                    record_data[field_key] = record.get(field_key)
        return binding_data, record_data, error

    @api.model
    def get_relational_value(self, model, id, dependencies):
        external_key = dependencies.get(model, {}).get(str(id)).get('external_key')
        _, sub_record = self.env['bus.binder'].get_record_by_external_key(external_key, model)
        return sub_record and sub_record.id or False

    def get_multiple_relational_value(self, model, ids, dependencies):
        result_ids = []
        for id in ids:
            result_ids.append(self.get_relational_value(model, id, dependencies))
        return result_ids
