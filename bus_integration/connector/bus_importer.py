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

from openerp.addons.connector.unit.mapper import mapping, ImportMapper

from .backend import BUSEXTEND
from ..unit.import_synchronizer import BusextendImporter


# TODO: à relire et comprendre
@BUSEXTEND
class BusMapperImportMapper(ImportMapper):
    _model_name = 'bus.receive.transfer'

    direct = [('_bus_model', 'model'), ('external_key', 'external_key')]

    @mapping
    def automap(self, record):
        rep = {}
        model_map = self.env['bus.object.mapping'].search([('name', '=', record.get('_bus_model')),
                                                       ('active', '=', True),
                                                       ('transmit', '=', True)])
        if model_map:
            dependency = record.get('_dependency', False)
            for field in model_map.field_ids:
                if field.active and field.import_field and field.map_name in record:
                    if field.type_field == 'many2many':
                        if not dependency:
                            raise ValueError(
                                u"Relational field must be imported while there are no dependencies (%s,%s)" % (
                                    model_map.name, field.name))
                        external_ids = str(record.get(field.name).get('ids'))
                        rep[field.name] = self.get_dependancies_local_id(dependency, field.relation,
                                                                           external_ids)
                    elif field.type_field == 'many2one':
                        if not dependency:
                            raise ValueError(
                                u"Relational field must be imported while there are no dependencies (%s,%s)" % (
                                    model_map.name, field.name))
                        external_id = str(record.get(field.name).get('id'))
                        rep[field.name] = self.get_dependancy_local_id(dependency, field.relation, external_id)
                    else:
                        rep[field.name] = record.get(field.map_name, False)

        return rep

    def get_dependancy_local_id(self, dependency, model, id):
        local_id = False
        field_dependency = dependency.get(model, False).get(str(id), False)
        if field_dependency:
            fk = self.env['bus.receive.transfer'].search([('external_key', '=', field_dependency.get('external_key')),
                                                      ('model', '=', field_dependency.get('_bus_model'))])
            local_id = fk and fk.local_id or False
        if not local_id:
            raise ValueError("Dependancy not satisfied, not no local_id for %s  key : %s" %
                             (model, field_dependency.get('external_key')))
        return local_id

    def get_dependancies_local_id(self, dependency, model, ids):
        new_vals = []
        for id in eval(ids):
            new_vals.append(self.get_dependancy_local_id(dependency, model, id) or False)
        return [(6, 0, new_vals)]


@BUSEXTEND
class BusImporter(BusextendImporter):
    _model_name = ['bus.receive.transfer']


BusImporter = BusImporter
