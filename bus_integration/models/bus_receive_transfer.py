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

import json
from openerp import api, models
from openerp import fields


class BusReceiveTransfer(models.Model):
    _name = 'bus.receive.transfer'
    _inherit = 'external.binding'

    model = fields.Char(string=u'Model', required=True, index=True)
    local_id = fields.Integer(string=u'Local ID', index=True)
    external_key = fields.Integer(string=u'External key', required=True, index=True)
    # used to check if data received from sender are new than local data
    origin_write_date = fields.Datetime(string=u"Sender write date")
    origin_base_id = fields.Many2one('bus.base', string=u"Sender", required=True, index=True)
    received_data = fields.Text(string=u"Received data (JSON-encoded)", required=True)
    to_deactivate = fields.Boolean(string=u"To deactivate")
    msg_error = fields.Text(string=u"Error message")

    _sql_constraints = [
        ('bus_uniq', 'unique(model, external_key)', u"A binding already exists with the same external key."),
        ('object_uniq', 'unique(model, local_id)', u"A binding already exists for this object"),
    ]

    def name_get(self):
        result = []
        for rec in self:
            local_record = self.env[rec.model].browse([rec.local_id])
            result.append((rec.id, u"%s → %s" % (rec.model, local_record.display_name)))
        return result

    @api.multi
    def view_local_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self.model,
            'res_id': self.local_id,
            'target': 'current',
        }

    @api.model
    def sanitize_vals(self, record, vals):
        newvals = self.remove_not_existing_fields(record._name, vals)
        newvals = self.remove_not_importable_fields(newvals)
        if record:
            newvals = self.get_vals_changed(record, newvals)
        return newvals

    @api.model
    def remove_not_importable_fields(self, vals):
        not_importable_field = ['xml_id', 'id', 'translation', 'external_key', 'bus_sender_id', 'bus_recipient_id']
        return {key: vals[key] for key in vals.keys() if key not in not_importable_field}

    @api.model
    def remove_not_existing_fields(self, model, vals):
        return {key: vals[key] for key in vals.keys() if key in self.env[model]._fields}

    @api.model
    def get_vals_changed(self, record, vals):
        change_vals = {}
        for val in vals:
            record_value = record[val]
            vals_value = vals.get(val)
            if isinstance(record_value, models.Model):
                if len(record_value) > 1:
                    record_value = record_value.ids
                    record_value.sort()
                    vals_value.sort()
                else:
                    record_value = record_value.id
            if val in record and vals_value != record_value:
                change_vals[val] = vals_value
        return change_vals

    def import_datas(self, transfer, odoo_record, transfer_vals, record_vals):
        received_record_write_date = json.loads(transfer_vals['received_data'])['write_date']
        if not transfer:
            # creates bus_receive_transfer record
            transfer_vals['origin_write_date'] = received_record_write_date
            transfer = self.create(self.remove_not_existing_fields(self._name, transfer_vals))
        else:
            if transfer.origin_write_date and fields.Datetime.from_string(transfer.origin_write_date) \
                    > fields.Datetime.from_string(received_record_write_date):
                # local data newer than received data.
                error_message = u'record %s not updated - external_key: %d - local data (%s) newer than ' \
                                'data received (%s)' % (transfer.display_name, transfer.external_key,
                                                        transfer.origin_write_date, received_record_write_date)
                return transfer, odoo_record, ('info', error_message)
            transfer.origin_write_date = received_record_write_date

        vals = self.sanitize_vals(odoo_record, record_vals)
        if not odoo_record:
            odoo_record = odoo_record\
                .with_context(bus_receive_transfer_external_key=transfer.external_key)\
                .create(vals)
        elif vals:
            odoo_record.write(vals)
        transfer.local_id = odoo_record.id
        return transfer, odoo_record, False
