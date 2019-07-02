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
from openerp import models, api


class BusSynchronizationBinder(models.AbstractModel):
    _name = 'bus.binder'

    @api.model
    def _get_transfer(self, external_key, model):
        transfer = self.env['bus.receive.transfer'].search([('external_key', '=', str(external_key)),
                                                            ('model', '=', str(model))], limit=1)
        return transfer

    @api.model
    def get_domain(self, field, domain, record, dependencies):
        domain_item = False
        value = record.get(field.field_name, False)
        if value:
            if isinstance(value, dict):
                external_id = str(value.get('id'))
                external_key = dependencies.get(field.relation_mapping_id.model_name).get(external_id).\
                    get('external_key')
                external_binding = self._get_transfer(external_key, field.relation_mapping_id.model_name)
                domain_item = (field.field_name, '=', external_binding.local_id)
            else:
                domain_item = (field.field_name, '=', value)
        if domain_item:
            domain.append(domain_item)
        return domain

    @api.model
    def get_record_by_xml(self, xml_id, model_name):
        module, name = xml_id.split(".")
        ir_model_data = self.env['ir.model.data'].search([('model', '=', model_name), ('module', '=', module),
                                                          ('name', '=', name)])
        return self.with_context(active_test=False).env[model_name].search([('id', '=', ir_model_data and
                                                                             ir_model_data.res_id or False)])

    @api.model
    def get_record_by_field_mapping(self, model_mapping, record, dependencies):
        odoo_record = self.env[model_mapping.model_name]
        fields_mapping = self.env['bus.object.mapping.field'].search([('is_migration_key', '=', True),
                                                                      ('mapping_id', '=', model_mapping.id)])
        domain = []
        if fields_mapping:
            for field in fields_mapping:
                domain = self.get_domain(field, domain, record, dependencies)
            if domain:
                odoo_record = odoo_record.with_context(active_test=False).search(domain)
        return odoo_record

    def get_record_by_external_key(self, external_key, model):
        transfer = self._get_transfer(external_key, model)
        return transfer, self.env[model].search([('id', '=', transfer and transfer.local_id or False)])

    @api.model
    def process_binding(self, record, model, external_key, model_mapping, dependencies, xml_id):
        transfer, odoo_record = self.get_record_by_external_key(external_key, model)
        if transfer:
            transfer.local_id = odoo_record.id
        else:
            if model_mapping.key_xml_id and xml_id:
                odoo_record = self.get_record_by_xml(xml_id, model_mapping.model_name)
            if not model_mapping.key_xml_id or not odoo_record:
                odoo_record = self.get_record_by_field_mapping(model_mapping, record, dependencies)

            if odoo_record and len(odoo_record) == 1:
                transfer = self.env['bus.receive.transfer'].create({
                    'model': model,
                    'local_id': odoo_record.id,
                    'external_key': external_key,
                    'received_data': json.dumps(record, indent=4)
                })
        return transfer, odoo_record
