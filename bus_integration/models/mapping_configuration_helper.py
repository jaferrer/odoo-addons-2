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

    field_ids = fields.One2many('mapping.configuration.helper.line', 'mapping_id', u"Fields to parameter",
                                domain=[('type_field', '!=', 'one2many'), ('is_computed', '=', False)])

    @api.onchange('model_id')
    def onchange_model_id(self):
        for rec in self:
            field_ids = False
            if rec.model_id:
                rec.field_ids = False
                mapping = self.env['bus.object.mapping'].get_mapping(rec.model_name)
                rec.key_xml_id = mapping.key_xml_id
                rec.deactivated_sync = mapping.deactivated_sync
                rec.deactivate_on_delete = mapping.deactivate_on_delete
                rec.is_exportable = mapping.is_exportable
                rec.is_importable = mapping.is_importable
                fields = self.env['ir.model.fields'].search([('model_id', '=', rec.model_id.id)])
                if fields:
                    field_ids = []
                mapping_fields = self.env['bus.object.mapping.field'].search([('mapping_id', '=', mapping.id)])
                for mapping_field in mapping_fields:
                    field_ids += [(0, 0, {
                        'model_id': rec.model_id.id,
                        'wizard_id': rec.id,
                        'field_id': mapping_field.field_id.id,
                        'map_name': mapping_field.map_name,
                        'export_field': mapping_field.export_field,
                        'import_creatable_field': mapping_field.import_creatable_field,
                        'import_updatable_field': mapping_field.import_updatable_field,
                        'is_migration_key': mapping_field.is_migration_key,
                    })]
            rec.field_ids = field_ids

    @api.multi
    def add_all(self):
        self.field_ids = []
        unwanted_fields = ('create_date', 'create_uid', '__last_update', 'write_date', 'write_uid', 'display_name')

        fields = self.env['ir.model.fields'].search(['&',
                                                     ('model_id', '=', self.model_id.id),
                                                     ('name', 'not in', unwanted_fields)])

        self.field_ids = self.env['mapping.configuration.helper.line']
        for field in fields:
            self.field_ids |= self.env['mapping.configuration.helper.line'].create({
                'model_id': self.model_id.id,
                'wizard_id': self.id,
                'field_id': field.id,
                'map_name': field.name,
                'export_field': self.is_exportable,
                'import_creatable_field': self.is_importable,
                'import_updatable_field': self.is_importable,
                'is_migration_key': False,
            })

        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            'view_type': 'form',
            "res_model": self._name,
            "res_id": self.id,
            "target": "new",
        }

    @api.multi
    def validate(self):
        self.ensure_one()
        model_mapping_xml_id = u"mapping_model_%s" % (self.model_id.model.replace('.', '_'))
        model_xml_id = self.model_id.get_external_id().get(self.model_id.id)
        model_configuration = u"%s,%s,%s,%s,%s,%s,%s" % (model_mapping_xml_id,
                                                         model_xml_id,
                                                         self.is_exportable,
                                                         self.is_importable,
                                                         self.key_xml_id,
                                                         self.deactivated_sync,
                                                         self.deactivate_on_delete)
        fields_configuration = u""""""
        for wizard_line in self.field_ids:
            field_mapping_xml_id = u"mapping_field_%s_%s" % (self.model_id.model.replace('.', '_'),
                                                             wizard_line.field_id.name)
            field_xml_id = wizard_line.field_id.get_external_id().get(wizard_line.field_id.id)
            fields_configuration += u"""%s,%s,%s,%s,%s,%s,%s,%s""" % (field_mapping_xml_id,
                                                                      model_mapping_xml_id,
                                                                      field_xml_id,
                                                                      wizard_line.map_name,
                                                                      wizard_line.export_field,
                                                                      wizard_line.import_creatable_field,
                                                                      wizard_line.import_updatable_field,
                                                                      wizard_line.is_migration_key)
            if wizard_line != self.field_ids[-1]:
                fields_configuration += u"""\n"""
        vals = {
            'model_configuration': model_configuration,
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

    mapping_id = fields.Many2one('mapping.configuration.helper', u"Wizard")

    @api.onchange('field_id')
    @api.multi
    def onchange_field_id(self):
        for rec in self:
            rec.map_name = rec.field_id and rec.field_id.name or u""


class MappingConfigurationHelperAnswer(models.TransientModel):
    _name = 'mapping.configuration.helper.answer'

    model_configuration_header = fields.Char(string=u"Model configuration header",
                                             compute="_compute_static_fields",
                                             store=False, readonly=True)
    fields_configuration_header = fields.Char(string=u"Fields configuration header",
                                              compute="_compute_static_fields",
                                              store=False, readonly=True)

    model_configuration = fields.Text(string=u"Model configuration")
    fields_configuration = fields.Text(string=u"Fields configuration")

    def _compute_static_fields(self):
        for rec in self:
            rec.fields_configuration_header = u"id,mapping_id:id,field_id:id,map_name,export_field," \
                                              u"import_creatable_field,import_updatable_field,is_migration_key"
            rec.model_configuration_header = u"id,model_id:id,is_exportable,is_importable,key_xml_id," \
                                             u"deactivated_sync,deactivate_on_delete"
