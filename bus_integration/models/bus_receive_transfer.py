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


from openerp import api, models
from openerp import fields


class BusReceiveTransfer(models.Model):
    _name = 'bus.receive.transfer'
    _inherit = 'external.binding'

    model = fields.Char(string=u'Model', required=True, index=True)
    local_id = fields.Integer(string=u'Local ID')
    external_key = fields.Integer(string=u'External key')
    received_data = fields.Text(string=u"Received data (JSON-encoded)", required=True)
    to_deactivate = fields.Boolean(string=u"To deactivate")

    _sql_constraints = [
        # TODO : a revoir unique sur external key, surement rajouter model
        ('bus_uniq', 'unique(model, external_key)', u"A binding already exists with the same external key."),
        ('object_uniq', 'unique(model, local_id)', u"A binding already exists for this object"),
    ]

    @api.model
    def remove_not_existing_fields(self, model, vals):
        return {key: vals[key] for key in vals.keys() if key in self.env[model]._fields}

    def import_datas(self, transfer, odoo_record, transfer_vals, record_vals):
        if not transfer:
            transfer = self.create(self.remove_not_existing_fields(self._name, transfer_vals))
        if not odoo_record:
            odoo_record = odoo_record.create(self.remove_not_existing_fields(odoo_record._name, record_vals))
        else:
            odoo_record.write(self.remove_not_existing_fields(odoo_record._name, record_vals))
        transfer.local_id = odoo_record.id
        return transfer, odoo_record
