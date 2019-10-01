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
            if rec.model_id:
                mapping = self.env['bus.object.mapping'].get_mapping(rec.model_name)
                rec.key_xml_id = mapping.key_xml_id
                rec.deactivated_sync = mapping.deactivated_sync
                rec.deactivate_on_delete = mapping.deactivate_on_delete
                rec.is_exportable = mapping.is_exportable
                rec.is_importable = mapping.is_importable
                rec.field_ids = False

    @api.multi
    def show_config(self):
        self.ensure_one()
        self.field_ids = self.env['mapping.configuration.helper.line']
        mapping = self.env['bus.object.mapping'].get_mapping(self.model_name)
        mapping_fields = self.env['bus.object.mapping.field'].search([('mapping_id', '=', mapping.id)])
        for mapping_field in mapping_fields:
            self.field_ids |= self.env['mapping.configuration.helper.line'].create({
                'wizard_id': self.id,
                'field_id': mapping_field.field_id.id,
                'map_name': mapping_field.map_name,
                'export_field': mapping_field.export_field,
                'import_creatable_field': mapping_field.import_creatable_field,
                'import_updatable_field': mapping_field.import_updatable_field,
                'is_migration_key': mapping_field.is_migration_key,
            })
        return self._get_refresh_action()

    def _get_refresh_action(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }

    @api.multi
    def add_all(self):
        self.field_ids = []
        unwanted_fields = ('id', 'display_name',
                           'create_date', 'create_uid',
                           'write_date', 'write_uid',
                           '__last_update')

        model_fields = self.env['ir.model.fields'].search([('model_id', '=', self.model_id.id),
                                                           ('name', 'not in', unwanted_fields)])

        self.field_ids = self.env['mapping.configuration.helper.line']
        for field in model_fields:
            self.field_ids |= self.env['mapping.configuration.helper.line'].create({
                'wizard_id': self.id,
                'field_id': field.id,
                'map_name': field.name,
                'export_field': self.is_exportable,
                'import_creatable_field': self.is_importable,
                'import_updatable_field': self.is_importable,
                'is_migration_key': False,
            })
        return self._get_refresh_action()

    @api.multi
    def validate(self):
        self.ensure_one()
        model_configuration, fields_configuration = self._get_mapping_as_csv()
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
            rec.fields_configuration_header = u"id,mapping_id:id,field_id_name,map_name,export_field," \
                                              u"import_creatable_field,import_updatable_field,is_migration_key"
            rec.model_configuration_header = u"id,model_id:id,is_exportable,is_importable,key_xml_id," \
                                             u"deactivated_sync,deactivate_on_delete"
