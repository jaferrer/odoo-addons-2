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

from openerp import api, models
from openerp import fields, exceptions, _ as _t
from ..connector.jobs import job_receive_message
import json

class BusReceiveTransfer(models.Model):
    _name = 'bus.receive.transfer'
    _inherit = 'external.binding'

    model = fields.Char(string=u'Model', required=True, index=True)
    local_id = fields.Integer(string=u'Local ID')
    external_key = fields.Integer(string=u'External key')
    received_data = fields.Text(string=u"Received data (JSON-encoded)", required=True)
    to_deactivate = fields.Boolean(string=u"To deactivate")

    _sql_constraints = [
        ('bus_uniq', 'unique(external_key)', u"A binding already exists with the same external key."),
        ('object_uniq', 'unique(model, local_id)', u"A binding already exists for this object"),
    ]

    @api.model
    def remove_not_existing_fields(self, model, vals):
        return {key: vals[key] for key in vals.keys() if key in self.env[model]._fields}

    @api.model
    def create(self, vals):
        model = vals.get('model')
        received_data = vals.get('received_data', "{}")
        if not vals.get('local_id'):
            if not self.env.context.get('migration', False):
                raise exceptions.except_orm(_t(u"Error"), _t(u"No matching for %s external_id : %s") %
                                            (vals.get('model'), vals.get('external_key', '')))
            try:
                # We remove fields that were sent but do not exist in the model
                created_record = self.env[model].create(self.remove_not_existing_fields(model,
                                                                                        json.loads(received_data)))
            except Exception:
                raise ValueError(u"Impossible to create %s with data : %s" % (vals.get('model'), received_data))
            vals.update({'local_id': created_record.id})
        return super(BusReceiveTransfer, self).create(vals)

    @api.multi
    def write(self, vals):
        for rec in self:
            model = vals.get('model')
            if model:
                local_id = vals.get('local_id', rec.local_id)
                received_data = vals.get('received_data', rec.received_data) or "{}"
                object = self.env[model].search([('id', '=', local_id)])
                safe_values = self.remove_not_existing_fields(model, received_data)
                if self.env.context.get('migration'):
                    if object:
                        try:
                            object.write(safe_values)
                        except Exception:
                            raise ValueError(u"Impossible to update %s, id: %s with data : %s" %
                                             (model, object.id, safe_values))
                    else:
                        try:
                            object = self.env[model].create(safe_values)
                        except Exception:
                            raise ValueError(u"Impossible to create %s with data : %s" % (model, safe_values))
                        vals.update({'local_id': object.id})
        return super(BusReceiveTransfer, self).write(vals)

    @api.model
    def receive_message(self, message_string, jobify=True):
        backend = self.env.ref('bus_integration.backend')
        message_dict = json.loads(message_string)
        message = self.env['bus.message'].create_message(message_dict, type='received')
        if jobify:
            return job_receive_message.delay(ConnectorSession.from_env(self.env),
                                             backend._name, backend.id, message_dict, message.id)
        return job_receive_message(ConnectorSession.from_env(self.env),
                                   backend._name, backend.id, message_dict, message.id)
