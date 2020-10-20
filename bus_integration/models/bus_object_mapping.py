# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import logging
from openerp.addons.bus_integration.models.bus_synchronized_model_abstract import BusSynchronizedModelAbstract
from openerp import models, fields, api, exceptions, _ as _t

_logger = logging.getLogger(__name__)


class BusObjectMappingAbstract(models.AbstractModel):
    _name = 'bus.object.mapping.abstract'

    model_id = fields.Many2one('ir.model', u"Model", required=True, context={'display_technical_names': True})
    model_name = fields.Char(u"Model name", readonly=True, related='model_id.model', store=True)

    field_ids = fields.One2many('bus.object.mapping.field.abstract', 'mapping_id', string=u"Fields")

    is_exportable = fields.Boolean(u"Is exportable")
    is_importable = fields.Boolean(u"Is importable")
    key_xml_id = fields.Boolean(string=u"Migration key on xml id",
                                help=u"if XML id not find, is_importable on key in fields")
    deactivated_sync = fields.Boolean(string=u"Synchronize inactive items")
    deactivate_on_delete = fields.Boolean(string=u"Deactivate on delete")
    update_prohibited = fields.Boolean(string=u"Update prohibited", help=u"When field are importable", default=True)

    @api.constrains('model_id', 'is_exportable')
    def _check_validity(self):
        for rec in self:
            if rec.is_exportable and not isinstance(self.env[rec.model_id.model], BusSynchronizedModelAbstract):
                raise exceptions.except_orm(u"error", u"Bus exported model '%s' must inherit from '%s'" %
                                            (rec.model_id.name, BusSynchronizedModelAbstract._name))

    @api.multi
    def name_get(self):
        return [(rec.id, u"%s mapping" % rec.model_id.model) for rec in self]

    @api.multi
    def view_datas(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': self.model_name,
            'target': 'new',
        }

    @api.multi
    def _get_mapping_as_csv(self):
        self.ensure_one()
        model_mapping_xml_id = u"mapping_model_%s" % (self.model_id.model.replace('.', '_'))
        model_xml_id = self.model_id.get_external_id().get(self.model_id.id)
        model_csv = u"%s,%s,%s,%s,%s,%s,%s,%s" % (model_mapping_xml_id,
                                                  model_xml_id,
                                                  self.is_exportable,
                                                  self.is_importable,
                                                  self.key_xml_id,
                                                  self.deactivated_sync,
                                                  self.deactivate_on_delete,
                                                  self.update_prohibited)

        fields_csv = u""""""
        for my_field in self.field_ids:
            field_mapping_xml_id = u"mapping_field_%s_%s" % (self.model_id.model.replace('.', '_'),
                                                             my_field.field_id.name)
            # removes the module from the xml id to compose the field_id_name
            field_id_name = my_field.field_id.get_external_id().get(my_field.field_id.id)
            idx = field_id_name.index('.')
            field_id_name = field_id_name[idx + 1:]
            fields_csv += u"""%s,%s,%s,%s,%s,%s,%s,%s""" % (field_mapping_xml_id,
                                                            model_mapping_xml_id,
                                                            field_id_name,
                                                            my_field.map_name,
                                                            my_field.export_field,
                                                            my_field.import_creatable_field,
                                                            my_field.import_updatable_field,
                                                            my_field.is_migration_key)
            if my_field != self.field_ids[-1]:
                fields_csv += u"""\n"""

        return model_csv, fields_csv

    @api.multi
    def display_config_popup(self):
        model_configuration = u""""""
        fields_configuration = u""""""
        for rec in self:
            if rec != self[0]:
                model_configuration += u"""\n"""
                fields_configuration += u"""\n"""

            rec_model_csv, rec_fields_csv = rec._get_mapping_as_csv()
            model_configuration += rec_model_csv
            fields_configuration += rec_fields_csv

        answer = self.env['mapping.configuration.helper.answer'].create({
            'model_configuration': model_configuration,
            'fields_configuration': fields_configuration,
        })

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

    @api.model
    def get_mapping_fields(self):
        self.ensure_one()
        return [field for field in self.field_ids if field.is_migration_key]


class BusObjectMappingFieldAbstract(models.AbstractModel):
    _name = 'bus.object.mapping.field.abstract'

    field_id = fields.Many2one('ir.model.fields', u"Field", required=True, context={'display_technical_names': True})

    mapping_id = fields.Many2one('bus.object.mapping.abstract', string=u"Model")
    model_id = fields.Many2one('ir.model', u"Model", related='mapping_id.model_id', readonly=True)

    # related fields
    field_name = fields.Char(u"Field name", readonly=True, related='field_id.name', store=True)
    type_field = fields.Selection(u"Type", related='field_id.ttype', store=True, readonly=True)
    is_computed = fields.Boolean(String=u"Computed", compute="_compute_depends_field_id", store=True)
    relation = fields.Char(u"relation", related="field_id.relation")
    # compute when model changes in mapping.field.configuration.helper
    map_name = fields.Char(u"Mapping name", required=True)
    # set manually
    export_field = fields.Boolean(u"To export")
    import_creatable_field = fields.Boolean(u"Import - to create")
    import_updatable_field = fields.Boolean(u"Import - to update")
    is_migration_key = fields.Boolean(u"Migration key", default=False)

    relation_mapping_id = fields.Many2one('bus.object.mapping', string='relation mapping',
                                          compute="_compute_depends_field_id", store=True)

    @api.multi
    @api.depends('field_id')
    def _compute_depends_field_id(self):
        for rec in self:
            model_name = rec.field_id.model
            rec.is_computed = model_name \
                and rec.field_name in self.env[model_name]._fields \
                and self.env[model_name]._fields[rec.field_name].compute \
                and not self.env[model_name]._fields[rec.field_name].store \
                and not self.env[model_name]._fields[rec.field_name].inverse \
                and not self.env[model_name]._fields[rec.field_name].related or False
            model_name = rec.field_id.relation
            mapping = self.env['bus.object.mapping'].search([('model_name', '=', model_name)])
            rec.relation_mapping_id = mapping


class BusObjectMapping(models.Model):
    _name = 'bus.object.mapping'
    _inherit = 'bus.object.mapping.abstract'
    _order = 'dependency_level ASC, model_name ASC'

    active = fields.Boolean(u"Active", default=True)
    field_ids = fields.One2many('bus.object.mapping.field', 'mapping_id', string=u"Fields",
                                domain=[('is_computed', '=', False)])
    dependency_level = fields.Integer(u"Dependency level", readonly=True)

    _sql_constraints = [
        ('model_id_uniq', 'unique(model_id)', u"A mapping object already exists with the same model."),
    ]

    @api.multi
    def compute_dependency_level(self):
        for rec in self:
            rec.dependency_level = 0  # reset value to re-calculate it
            rec._calculate_dep_level(rec, 0)

    @api.multi
    def _calculate_dep_level(self, current_mapping, model_deps_seen=None):
        self.ensure_one()

        if not model_deps_seen:
            model_deps_seen = [current_mapping.model_name]

        # save current level in model if higher than the one we know
        if len(model_deps_seen) - 1 > self.dependency_level:
            self.dependency_level = len(model_deps_seen) - 1

        for field in current_mapping.field_ids:
            if field.relation_mapping_id and field.relation_mapping_id.model_name not in model_deps_seen:
                # go deeper.. recursively
                branch_models = list(model_deps_seen)
                branch_models.append(field.relation_mapping_id.model_name)
                self._calculate_dep_level(field.relation_mapping_id, branch_models)

    @api.constrains('deactivate_on_delete', 'deactivated_sync')
    def _contrains_deactivate_on_delete(self):
        # We do not map the obsolete tables
        if self.model_id.model in self.env.registry and 'active' not in self.env[self.model_id.model]._fields and \
                (self.deactivate_on_delete or self.deactivated_sync):
            raise exceptions.except_orm(_t(u"Error"),
                                        _t(u"This model must have the field 'active', (%s)" % self.model_id.model))

    @api.model
    def get_mapping(self, model_name):
        domain = [('model_name', '=', model_name)]
        try:
            return self.env['bus.object.mapping'].search(domain, limit=1)
        except ValueError:  # catch exception to enable bus_integration uninstall
            return self.env['bus.object.mapping']

    @api.multi
    def open_object_configuration(self):
        self.ensure_one()
        wizard = self.env['mapping.configuration.helper'].create({'model_id': self.model_id.id})
        wizard.onchange_model_id()
        return {
            'name': u"Mapping configuration helper",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mapping.configuration.helper',
            'res_id': wizard.id,
            'target': 'new',
            'context': self.env.context
        }

    @api.multi
    def export_config(self):
        return super(BusObjectMapping, self).display_config_popup()

    @api.multi
    def get_field_to_export(self):
        self.ensure_one()
        return [field for field in self.field_ids if field.export_field]

    @api.multi
    def get_field_to_import(self):
        self.ensure_one()
        return [field for field in self.field_ids if field.import_creatable_field or field.import_updatable_field]

    @api.model
    def delete_records_created_manually(self):
        for rec in self.search([]):
            xml_id = rec.get_external_id().get(rec.id, '')
            if not xml_id:
                _logger.info(u"Deleting mapping for model %s, because it was created manually.", rec.model_name)
                rec.unlink()


class BusObjectMappingField(models.Model):
    _name = 'bus.object.mapping.field'
    _inherit = 'bus.object.mapping.field.abstract'

    mapping_id = fields.Many2one('bus.object.mapping', string=u"Model")
    # "field_id_name" = temporary field used while importing data from CSV to compute "field_id"
    field_id_name = fields.Text(string="field_name", store=False, compute=lambda x: [None for _ in x], required=False)
    active = fields.Boolean(u"Active", default=True)

    _sql_constraints = [
        ('name_uniq_by_model', 'unique(field_id, mapping_id)', u"This field already exists for this model."),
    ]

    def _get_vals_with_field_id(self, vals):
        if 'field_id_name' not in vals:
            return vals
        #  import from csv, required 'field_id' must be computed from field_id_name
        field_data = self.env['ir.model.data'].search([('name', '=', vals['field_id_name']),
                                                       ('model', '=', 'ir.model.fields')])
        if not field_data:
            raise exceptions.ValidationError(
                'bus.object.mapping.csv error : No field found with name: ' + vals['field_id_name'])
        vals['field_id'] = field_data.res_id
        return vals

    @api.model
    def delete_records_created_manually(self):
        for rec in self.search([]):
            xml_id = rec.get_external_id().get(rec.id, '')
            if not xml_id:
                _logger.info(u"Deleting mapping for field %s in model %s, because it was created manually.",
                             rec.field_name, rec.mapping_id.model_name)
                rec.unlink()

    @api.model
    def create(self, vals):
        vals = self._get_vals_with_field_id(vals)
        return super(BusObjectMappingField, self).create(vals)

    @api.multi
    def write(self, vals):
        vals = self._get_vals_with_field_id(vals)
        return super(BusObjectMappingField, self).write(vals)
