# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import models, fields, api


class AccountInvoiceChangeType(models.Model):
    _name = 'account.invoice.change.date.number'

    invoice_id = fields.Many2one('account.invoice', string=u"Invoice", readonly=True, required=True)
    new_date = fields.Date(string=u"New Date")
    new_number = fields.Char(string=u"New Number")
    done = fields.Boolean(string=u"Done", readonly=True)

    @api.multi
    def apply(self):
        self.ensure_one()
        invoice_dict = {}
        move_dict = {}
        if self.new_date:
            invoice_dict['date_invoice'] = self.new_date
            move_dict['date'] = self.new_date
        if self.new_number:
            invoice_dict['number'] = self.new_number
            move_dict['name'] = self.new_number
        self.invoice_id.write(invoice_dict)
        self.invoice_id.move_id.write(move_dict)
        self.done = True
        return {'type': 'ir.actions.act_window_close'}
