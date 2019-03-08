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


class SirailConfig(models.TransientModel):
    _name = "sirail.config.mapping"

    @api.model
    def update_mapping(self):
        model_mapping_ids = self.env["object.mapping"].search([])

        model_mapping_ids.write({
            "active": False
        })

        for mod_map in model_mapping_ids:
            mod_map.field_ids.write({
                "active": False
            })

        model_ids = self.env["ir.model"].search([])
        for model in model_ids:
            map_model = self.env["object.mapping"].search([("name", "=", model.model),
                                                           ("active", "=", False)])
            if not map_model:
                map_model = self.env['object.mapping'].create({
                    "name": model.model,
                    "transmit": False,
                    "active": True
                })
            else:
                map_model.write({
                    "active": True,
                    'migration': False,
                    'transmit': False,
                    'key_xml_id': False
                })
            # Used to make references in xml
            model_data_name = "object.mapping." + model.model
            model_data_name = model_data_name.replace(".", "_")
            map_model_data = self.env['ir.model.data'].search([('name', '=', model_data_name),
                                                               ('module', '=', 'created_by_bus'),
                                                               ('model', '=', 'object.mapping')])
            if not map_model_data:
                self.env['ir.model.data'].create({
                    'name': model_data_name.replace(".", "_"),
                    'module': "created_by_bus",
                    'model': "object.mapping",
                    'res_id': map_model.id
                })

            field_ids = self.env["ir.model.fields"].search([("model_id", "=", model.id),
                                                            ("ttype", "not in", ["one2many", "binary"])])

            for field in field_ids:
                map_field = self.env["object.mapping.field"].search([("object_id", "=", map_model.id),
                                                                     ("name", "=", field.name),
                                                                     ("active", "=", False)])
                if field.ttype == "many2one":
                    field_type = "M2O"
                elif field.ttype == "many2many":
                    field_type = "M2M"
                else:
                    field_type = "PRIMARY"

                if not map_field:
                    map_field = self.env['object.mapping.field'].create({
                        "object_id": map_model.id,
                        "name": field.name,
                        "map_name": field.name,
                        "type_field": field_type,
                        "relation": field.relation,
                        "active": True,
                    })
                else:
                    map_field.write({
                        "type_field": field_type,
                        "relation": field.relation,
                        "active": True,
                        'migration': False,
                        'export_field': False,
                        'import_field': False
                    })
                # Used to make references in xml for configuration
                model_data_name_field = "object.mapping.field." + model.model + "." + field.name
                model_data_name_field = model_data_name_field.replace('.', '_')
                map_field_data = self.env['ir.model.data'].search([('name', '=', model_data_name_field),
                                                                   ('module', '=', 'created_by_bus'),
                                                                   ('model', '=', 'object.mapping.field')])

                if not map_field_data:
                    map_field_data = self.env['ir.model.data'].create({
                        'name': model_data_name_field.replace(".", "_"),
                        'module': "created_by_bus",
                        'model': "object.mapping.field",
                        'res_id': map_field.id
                    })
                else:
                    map_field_data.write({
                        'name': model_data_name_field.replace(".", "_"),
                        'module': "created_by_bus",
                        'model': "object.mapping.field",
                        'res_id': map_field.id
                    })
