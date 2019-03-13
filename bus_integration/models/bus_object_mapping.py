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

from openerp import models, fields, api, exceptions, _ as _t


class BusObjectMappingAbstract(models.AbstractModel):
    _name = 'bus.object.mapping.abstract'

    model_id = fields.Many2one('ir.model', u"Model", required=True)
    key_xml_id = fields.Boolean(string=u"Migration key on xml id",
                                help=u"if XML id not find, is_importable on key in fields")
    deactivated_sync = fields.Boolean(string=u"Synchronize inactive items")
    deactivate_on_delete = fields.Boolean(string=u"Deactivate on delete")

    @api.multi
    def name_get(self):
        return [(rec.id, u"Mapping of object %s" % rec.model_id.name) for rec in self]


class BusObjectMappingFieldAbstract(models.AbstractModel):
    _name = 'bus.object.mapping.field.abstract'

    field_id = fields.Many2one('ir.model.fields', u"Field", required=True,
                               context={'display_technical_field_names': True})
    type_field = fields.Selection(u"Type", related='field_id.ttype', store=True, readonly=True)
    relation = fields.Char(string=u'Relation', related='field_id.relation', store=True, readonly=True)
    map_name = fields.Char(u"Mapping name", required=True)
    export_field = fields.Boolean(u"To export")
    import_field = fields.Boolean(u"To import")
    is_migration_key = fields.Boolean(u"Migration key", default=False)


class BusObjectMapping(models.Model):
    _name = 'bus.object.mapping'
    _inherit = 'bus.object.mapping.abstract'

    active = fields.Boolean(u"Active", default=True)
    is_exportable = fields.Boolean(u"Is exportable", compute='_compute_export_data', store=True)
    is_importable = fields.Boolean(u"Is importable", compute='_compute_export_data', store=True)
    field_ids = fields.One2many('bus.object.mapping.field', 'mapping_id', string=u"Fields")

    _sql_constraints = [
        ('model_id_uniq', 'unique(model_id)', u"A mapping object already exists with the same model."),
    ]

    @api.constrains('deactivate_on_delete', 'deactivated_sync')
    def _contrains_deactivate_on_delete(self):
        # We do not map the obsolete tables
        if self.model_id.model in self.env.registry and 'active' not in self.env[self.model_id.model]._fields and \
                (self.deactivate_on_delete or self.deactivated_sync):
            raise exceptions.except_orm(_t(u"Error"),
                                        _t(u"This model must have the field 'active', (%s)" % self.model_id.model))

    @api.depends('field_ids', 'field_ids.type_field', 'field_ids.export_field', 'field_ids.import_field')
    @api.multi
    def _compute_export_data(self):
        for rec in self:
            rec.is_exportable = any([field.export_field for field in rec.field_ids])
            rec.is_importable = any([field.import_field for field in rec.field_ids])

    @api.model
    def get_mapping(self, model_name, only_transmit=False):
        domain = [('model_id.name', '=', model_name)]
        if only_transmit:
            only_transmit += [('is_exportable', '=', True)]
        return self.env['bus.object.mapping'].search(domain, limit=1)

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


class BusObjectMappingField(models.Model):
    _name = 'bus.object.mapping.field'
    _inherit = 'bus.object.mapping.field.abstract'

    mapping_id = fields.Many2one('bus.object.mapping', string=u"Model")
    active = fields.Boolean(u"Active", default=True)
    model_id = fields.Many2one('ir.model', u"Model", related='mapping_id.model_id', readonly=True)

    _sql_constraints = [
        ('name_uniq_by_model', 'unique(field_id, mapping_id)', u"This field already exists for this model."),
    ]
