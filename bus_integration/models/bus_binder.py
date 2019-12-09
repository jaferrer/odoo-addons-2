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
import logging
from openerp import models, api

_logger = logging.getLogger(__name__)


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
        fields_mapping = model_mapping.get_mapping_fields()
        domain = []
        if fields_mapping:
            for field in fields_mapping:
                domain = self.get_domain(field, domain, record, dependencies)
            if domain:
                odoo_record = odoo_record.with_context(active_test=False).search(domain)
        return odoo_record

    def get_record_by_external_key(self, external_key, model):
        transfer = self._get_transfer(external_key, model)
        local_id = transfer and transfer.local_id or False
        return transfer, self.with_context(active_test=False).env[model].search([('id', '=', local_id)])

    @api.model
    def is_valid_xml_id(self, xml_id):
        module, _ = xml_id.split(".")
        configuration = self.env.ref('bus_integration.backend')
        disabled_modules = configuration.module_disabled_mapping.split(',')
        if module in disabled_modules:
            return False
        return True

    @api.model
    def process_binding(self, record, model, external_key, model_mapping, message, xml_id):

        def get_log(odoo_record):
            if not odoo_record:
                return "NO LOCAL RECORD FOUND"
            elif len(odoo_record) == 1:
                return "FOUND LOCAL ID #%d (%s)" % (odoo_record.id, odoo_record.display_name)
            return "ERROR, MULTIPLE RECORDS FOUND"

        errors = []
        transfer, odoo_record = self.get_record_by_external_key(external_key, model)
        if transfer:
            transfer.local_id = odoo_record.id
        else:
            log_message = ""
            if model_mapping.key_xml_id and xml_id and self.is_valid_xml_id(xml_id):
                odoo_record = self.get_record_by_xml(xml_id, model_mapping.model_name)
                log_message = "bus-process_binding %s #%d (%s) by xml_id '%s': %s" % (model, external_key,
                                                                                      record['display_name'],
                                                                                      xml_id, get_log(odoo_record))
                _logger.info(log_message)

            if not model_mapping.key_xml_id or not odoo_record:
                odoo_record = self.get_record_by_field_mapping(model_mapping, record, message.get_json_dependencies())
                log_message = "bus-process_binding %s #%d (%s) by field mapping %s : %s" % (
                    model, external_key, record['display_name'],
                    str([field.field_name for field in model_mapping.get_mapping_fields()]),
                    get_log(odoo_record))
                _logger.info(log_message)

            if len(odoo_record) > 1:
                errors.append(('error', u"%s \n Too many local record found %s" % (log_message, odoo_record)))

            if odoo_record and len(odoo_record) == 1:
                existing_transfer = self.env['bus.receive.transfer'].search(
                    [('model', '=', model), ('local_id', '=', odoo_record.id)])
                if existing_transfer:
                    msg = '%s, cannot create bus_receive_transfer local record is already mapped ' \
                          'to external_key : #%d ' % (log_message, existing_transfer.external_key)
                    _logger.error(msg)
                    errors.append(('error', msg))
                else:
                    transfer = self.env['bus.receive.transfer'].create({
                        'model': model,
                        'local_id': odoo_record.id,
                        'external_key': external_key,
                        'received_data': json.dumps(record, indent=4),
                        'origin_base_id': message.get_base_origin().id,
                    })
        return transfer, odoo_record, errors
