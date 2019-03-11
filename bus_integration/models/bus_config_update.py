# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class BusConfigUpdate(models.TransientModel):
    _name = 'bus.config.update'

    @api.model
    def update_mapping(self):
        self.env['bus.object.mapping.field'].search([]).write({'active': False})
        self.env['bus.object.mapping'].search([]).write({'active': False})

        models = self.env['ir.model'].search([])
        for model in models:
            mapping = self.env['bus.object.mapping'].search([('name', '=', model.model), ('active', '=', False)])
            if not mapping:
                mapping = self.env['bus.object.mapping'].create({
                    'name': model.model,
                    'transmit': False,
                    'active': True
                })
            else:
                mapping.write({
                    'active': True,
                    'migration': False,
                    'transmit': False,
                    'key_xml_id': False
                })
            # Used to make references in xml
            model_data_name = 'bus.object.mapping.' + model.model
            model_data_name = model_data_name.replace('.', '_')
            map_model_data = self.env['ir.model.data'].search([('name', '=', model_data_name),
                                                               ('module', '=', 'created_by_bus'),
                                                               ('model', '=', 'bus.object.mapping')])
            if not map_model_data:
                self.env['ir.model.data'].create({
                    'name': model_data_name.replace(".", "_"),
                    'module': 'created_by_bus',
                    'model': 'bus.object.mapping',
                    'res_id': mapping.id
                })
            fields = self.env['ir.model.fields'].search([('model_id', '=', model.id),
                                                         ('ttype', 'not in', ['one2many', 'binary'])])
            for field in fields:
                mapping_field = self.env['bus.object.mapping.field'].search([('object_id', '=', mapping.id),
                                                                         ('name', '=', field.name),
                                                                         ('active', '=', False)])
                if field.ttype == 'many2one':
                    field_type = 'many2one'
                elif field.ttype == 'many2many':
                    field_type = 'many2many'
                else:
                    field_type = 'primary'
                if not mapping_field:
                    mapping_field = self.env['bus.object.mapping.field'].create({
                        'object_id': mapping.id,
                        'name': field.name,
                        'map_name': field.name,
                        'type_field': field_type,
                        'relation': field.relation,
                        'active': True,
                    })
                else:
                    mapping_field.write({
                        'type_field': field_type,
                        'relation': field.relation,
                        'active': True,
                        'migration': False,
                        'export_field': False,
                        'import_field': False
                    })
                # Used to make references in xml for configuration
                model_data_name_field = 'bus.object.mapping.field.%s.%s' % (model.model, field.name)
                model_data_name_field = model_data_name_field.replace('.', '_')
                mapping_field_data = self.env['ir.model.data'].search([('name', '=', model_data_name_field),
                                                                       ('module', '=', 'created_by_bus'),
                                                                       ('model', '=', 'bus.object.mapping.field')])
                if not mapping_field_data:
                    self.env['ir.model.data'].create({
                        'name': model_data_name_field.replace('.', '_'),
                        'module': 'created_by_bus',
                        'model': 'bus.object.mapping.field',
                        'res_id': mapping_field.id
                    })
                else:
                    mapping_field_data.write({
                        'name': model_data_name_field.replace('.', '_'),
                        'module': 'created_by_bus',
                        'model': 'bus.object.mapping.field',
                        'res_id': mapping_field.id
                    })
