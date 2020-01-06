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


class AccountInvoiceChangeType(models.TransientModel):
    _name = 'account.invoice.change.type'

    new_type = fields.Selection([('out_invoice', 'Customer Invoice'),
                                 ('in_invoice', 'Vendor Bill'),
                                 ('out_refund', 'Customer Refund'),
                                 ('in_refund', 'Vendor Refund')], string=u"New Type")

    @api.multi
    def change_type(self):
        self.ensure_one()
        if self.new_type:
            invoices = self.env['account.invoice'].browse(self.env.context.get('active_ids', []))
            invoices.write({'type': self.new_type})
        return {'type': 'ir.actions.act_window_close'}
