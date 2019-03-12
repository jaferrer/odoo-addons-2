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


class ObjectMapping(models.Model):
    _name = 'bus.object.mapping'

    name = fields.Char(u"Model", readonly=True)
    transmit = fields.Boolean(u"Communicable")
    active = fields.Boolean(u"Active", default=True)
    migration = fields.Boolean(u"Objet migrable", default=False)
    field_ids = fields.One2many('bus.object.mapping.field', 'object_id', string=u"Fields")
    key_xml_id = fields.Boolean(string=u"Migration key on xml id",
                                help=u"if XML id not find, migration on key in fields")
    deactivated_sync = fields.Boolean(string=u"Synchronize inactive items")
    deactivate_on_delete = fields.Boolean(string=u"Deactivate on delete")

    _sql_constraints = [
        ('name_uniq', 'unique(name)', u"A mapping object already exists with the same model."),
    ]

    @api.constrains('deactivate_on_delete', 'deactivated_sync')
    def _contrains_deactivate_on_delete(self):
        if "active" not in self.env[self.name]._fields and (self.deactivate_on_delete or self.deactivated_sync):
            raise exceptions.except_orm(_t(u"Error"), _t(u"This model must have the field 'active', (%s)" % self.name))

    @api.multi
    def write(self, vals):
        for rec in self:
            if vals.get('deactivated_sync', False):
                field = self.env['bus.object.mapping.field'].search([('object_id', '=', rec.id), ('name', '=', 'active')])
                if field:
                    field.write({'export_field': True, 'import_field': True, 'active': True})
        return super(ObjectMapping, self).write(vals)

    @api.model
    def get_mapping(self, model_name):
        return self.env['bus.object.mapping'].search([('name', '=', model_name)], limit=1)


class ObjectMappingField(models.Model):
    _name = 'bus.object.mapping.field'

    object_id = fields.Many2one('bus.object.mapping', string=u"Model")
    name = fields.Char(string=u"Name", readonly=True)
    map_name = fields.Char(string=u"Map name")
    type_field = fields.Selection([('primary', u"Primaire"),
                                   ('many2one', u"Object"),
                                   ('many2many', u"Objects")], readonly=True, string=u"Type")
    relation = fields.Char(string=u'Relation', readonly=True)
    export_field = fields.Boolean(u"Field to export")
    import_field = fields.Boolean(u"Field to import")
    active = fields.Boolean(u"Active", default=True)
    migration = fields.Boolean(u"Migration key", default=False)

    _sql_constraints = [
        ('name_uniq_by_model', 'unique(name, object_id)', u"This field already exists for this model."),
    ]

    @api.multi
    def write(self, vals):
        for rec in self:
            if rec.type_field == "many2one" and rec.relation and (vals.get("export_field") or vals.get("import_field")):
                mod = self.env['bus.object.mapping'].search([("name", "=", rec.relation)])
                mod.write({
                    "transmit": True
                })
        return super(ObjectMappingField, self).write(vals)

    @api.model
    def get_mapping_field(self, mapping, field_name):
        return self.env['bus.object.mapping.field'].search([('name', '=', field_name),
                                                        ('object_id', '=', mapping.id)], limit=1)
