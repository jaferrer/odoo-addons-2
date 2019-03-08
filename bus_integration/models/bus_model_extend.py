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

from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.unit.mapper import mapping, ImportMapper

from openerp import api, models
from openerp import fields, exceptions, _ as _t
from .. import jobs
from ..backend import BUSEXTEND
from ..unit.import_synchronizer import BusextendImporter


class BusextendBinding(models.AbstractModel):
    _name = 'busextend.binding'
    _inherit = 'external.binding'
    _description = 'busextend Binding (abstract)'

    external_key = fields.Integer(string=u'External_key')

    _sql_constraints = [
        ('bus_uniq', 'unique(external_key)',
         'A binding already exists with the same magento ID.'),
    ]


class BusModelExtend(models.Model):
    _name = 'bus.model.extend'
    _inherit = 'busextend.binding'

    model = fields.Char(string=u'Model', required=True, index=True)
    external_key = fields.Integer(string=u'External_key')
    openerp_id = fields.Integer(string=u'Openerp ID')
    to_deactivate = fields.Boolean(string=u"To deactivate")

    @api.model
    def create(self, vals):
        if not vals.get("openerp_id"):
            if not self.env.context.get("migration", False):
                raise exceptions.except_orm(_t(u"Error"), _t(
                    u"No matching for %s external_id : %s") % (vals.get("model"), vals.get("openerp_id")))
            try:
                openerp_id = self.env[vals.get("model")].create(self.extract_field_object(vals.get("model"), vals))
            except Exception:
                raise ValueError(u"Impossible to create %s with data : %s" % (vals.get("model"), vals))
            vals.update({"openerp_id": openerp_id})
        return super(BusModelExtend, self).create(self.extract_field_object(self._name, vals))

    @api.multi
    def write(self, vals):
        for rec in self:
            if vals.get("model", False):
                object = self.env[vals.get("model")].search([('id', '=', rec.openerp_id)])
                safe_values = self.extract_field_object(vals.get('model'), vals)
                if self.env.context.get("migration", False):
                    if object:
                        try:
                            object.write(safe_values)
                        except Exception:
                            raise ValueError(u"Impossible to update %s, id: %s with data : %s" % (
                                vals.get("model"), object.id, vals))
                    else:
                        try:
                            object = self.env[vals.get("model")].create(safe_values)
                        except Exception:
                            raise ValueError(u"Impossible to create %s with data : %s" % (vals.get("model"), vals))
                        vals.update({"openerp_id": object.id})
        return super(BusModelExtend, self).write(self.extract_field_object(self._name, vals))

    @api.model
    def receive_message(self, archive):
        self.sudo()
        jobs.job_receive_message.delay(
            ConnectorSession.from_env(self.env),
            'bus.model.extend',
            0,
            archive)
        return True

    def extract_field_object(self, model, vals):
        object = self.env[model]
        new_vals = {}
        for key in vals.keys():
            if key in object._fields:
                new_vals.update({key: vals[key]})
        return new_vals


@BUSEXTEND
class BusMapperImportMapper(ImportMapper):
    _model_name = 'bus.model.extend'

    direct = [('_bus_model', 'model'),
              ('external_key', 'external_key')]

    @mapping
    def automap(self, record):
        rep = {}
        model_map = self.env["object.mapping"].search([("name", "=", record.get("_bus_model")),
                                                       ("active", "=", True),
                                                       ("transmit", "=", True)])
        if model_map:
            dependency = record.get("_dependency", False)
            for field in model_map.field_ids:
                if field.active and field.import_field and field.map_name in record:
                    if field.type_field == "M2M":
                        if not dependency:
                            raise ValueError(
                                u"Relational field must be imported while there are no dependencies (%s,%s)" % (
                                    model_map.name, field.name))
                        external_ids = str(record.get(field.name).get('ids'))
                        rep[field.name] = self.get_dependancies_openerp_id(dependency, field.relation,
                                                                           external_ids)
                    elif field.type_field == "M2O":
                        if not dependency:
                            raise ValueError(
                                u"Relational field must be imported while there are no dependencies (%s,%s)" % (
                                    model_map.name, field.name))
                        external_id = str(record.get(field.name).get('id'))
                        rep[field.name] = self.get_dependancy_openerp_id(dependency, field.relation, external_id)
                    else:
                        rep[field.name] = record.get(field.map_name, False)

        return rep

    def get_dependancy_openerp_id(self, dependency, model, id):
        openerp_id = False
        field_dependency = dependency.get(model, False).get(str(id), False)
        if field_dependency:
            fk = self.env["bus.model.extend"].search([("external_key", "=", field_dependency.get("external_key")),
                                                      ("model", "=", field_dependency.get("_bus_model"))])
            openerp_id = fk and fk.openerp_id or False
        if not openerp_id:
            raise ValueError('Dependancy not satisfied, not '
                             'no openerp_id for %s  key : %s' % (model, field_dependency.get("external_key")))
        return openerp_id

    def get_dependancies_openerp_id(self, dependency, model, ids):
        new_vals = []
        for id in eval(ids):
            new_vals.append(self.get_dependancy_openerp_id(dependency, model, id) or False)
        return [(6, 0, new_vals)]


@BUSEXTEND
class BusImporter(BusextendImporter):
    _model_name = ['bus.model.extend']


BusImporter = BusImporter
