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

from openerp import models, fields, api


class MappingConfigurationHelper(models.TransientModel):
    _name = 'mapping.configuration.helper'
    _inherit = 'bus.object.mapping.abstract'

    helper_line_ids = fields.One2many('mapping.configuration.helper.line', 'wizard_id',
                                      u"Fields to parameter", required=True)

    @api.onchange('model_id')
    def onchange_model_id(self):
        for rec in self:
            helper_line_ids = False
            if rec.model_id:
                rec.helper_line_ids = False
                mapping = self.env['bus.object.mapping'].get_mapping(rec.model_id.name)
                rec.key_xml_id = mapping.key_xml_id
                rec.deactivated_sync = mapping.deactivated_sync
                rec.deactivate_on_delete = mapping.deactivate_on_delete
                rec.is_exportable = mapping.is_exportable
                rec.is_importable = mapping.is_importable
                fields = self.env['ir.model.fields'].search([('model_id', '=', rec.model_id.id)])
                if fields:
                    helper_line_ids = []
                mapping_fields = self.env['bus.object.mapping.field'].search([('mapping_id', '=', mapping.id)])
                for mapping_field in mapping_fields:
                    helper_line_ids += [(0, 0, {
                        'model_id': rec.model_id.id,
                        'wizard_id': rec.id,
                        'field_id': mapping_field.field_id.id,
                        'map_name': mapping_field.map_name,
                        'export_field': mapping_field.export_field,
                        'import_field': mapping_field.import_field,
                        'is_migration_key': mapping_field.is_migration_key,
                    })]
            rec.helper_line_ids = helper_line_ids

    @api.multi
    def validate(self):
        self.ensure_one()
        model_configuration_header = u"id,model_id:id,key_xml_id,deactivated_sync,deactivate_on_delete,is_exportable,is_importable"
        fields_configuration_header = u"id,mapping_id:id,field_id:id,map_name,export_field,import_field,is_migration_key"
        model_mapping_xml_id = u"mapping_model_%s" % (self.model_id.model.replace('.', '_'))
        model_xml_id = self.model_id.get_external_id().get(self.model_id.id)
        model_configuration = u"%s,%s,%s,%s,%s,%s,%s" % (model_mapping_xml_id,
                                                         model_xml_id,
                                                         self.key_xml_id,
                                                         self.deactivated_sync,
                                                         self.deactivate_on_delete,
                                                         self.is_exportable,
                                                         self.is_importable)
        fields_configuration = u""""""
        for wizard_line in self.helper_line_ids:
            field_mapping_xml_id = u"mapping_field_%s_%s" % (self.model_id.model.replace('.', '_'),
                                                             wizard_line.field_id.name)
            field_xml_id = wizard_line.field_id.get_external_id().get(wizard_line.field_id.id)
            fields_configuration += u"""%s,%s,%s,%s,%s,%s,%s""" % (field_mapping_xml_id,
                                                                   model_mapping_xml_id,
                                                                   field_xml_id,
                                                                   wizard_line.map_name,
                                                                   wizard_line.export_field,
                                                                   wizard_line.import_field,
                                                                   wizard_line.is_migration_key)
            if wizard_line != self.helper_line_ids[-1]:
                fields_configuration += u"""\n"""
        vals = {
            'model_configuration_header': model_configuration_header,
            'model_configuration':  model_configuration,
            'fields_configuration_header': fields_configuration_header,
            'fields_configuration': fields_configuration,
        }
        answer = self.env['mapping.configuration.helper.answer'].create(vals)
        return {
            'name': u"Mapping configuration helper",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mapping.configuration.helper.answer',
            'res_id': answer.id,
            'target': 'new',
            'context': self.env.context
        }


class MappingConfigurationHelperLine(models.TransientModel):
    _name = 'mapping.configuration.helper.line'
    _inherit = 'bus.object.mapping.field.abstract'

    wizard_id = fields.Many2one('mapping.configuration.helper', u"Wizard")
    model_id = fields.Many2one('ir.model', u"Model", related='wizard_id.model_id', readonly=True)

    @api.onchange('field_id')
    @api.multi
    def onchange_field_i(self):
        for rec in self:
            rec.map_name = rec.field_id and rec.field_id.name or u""


class MappingConfigurationHelperAnswer(models.TransientModel):
    _name = 'mapping.configuration.helper.answer'

    model_configuration_header = fields.Char(string=u"Model configuration header")
    fields_configuration_header = fields.Char(string=u"Fields configuration header")
    model_configuration = fields.Char(string=u"Model configuration")
    fields_configuration = fields.Text(string=u"Fields configuration")
