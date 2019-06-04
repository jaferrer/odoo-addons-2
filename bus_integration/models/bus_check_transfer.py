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

from openerp import models, api, fields


class CheckTransfer(models.Model):
    _name = 'bus.check.transfer'
    _order = 'create_date DESC'

    res_model = fields.Char(u"Model")
    res_id = fields.Integer(u"Local id")
    recipient_record_id = fields.Integer(u"Recipient record id")
    external_key = fields.Integer(u"External key")
    recipient_id = fields.Many2one('bus.base', u"Recipient")
    date_request = fields.Datetime(u"Request date")
    date_response = fields.Datetime(u"Response date")
    state = fields.Selection([('request', u"Requested"), ('find', u"Find"), ('not_find', u"Not find"),
                              ('error', u"Error")], u"State")

    @api.multi
    def view_local_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'target': 'current',
        }
