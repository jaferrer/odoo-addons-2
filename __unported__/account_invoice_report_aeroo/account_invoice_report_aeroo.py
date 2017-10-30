# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api


class AccountInvoiceDeleteReport(models.TransientModel):
    _name = 'account.invoice.delete.report'

    @api.model
    def delete_report(self):
        existing_report = self.env.ref('account.account_invoices')
        ir_value = self.env['ir.values']. \
            search([('value', '=', 'ir.actions.report.xml,' + unicode(existing_report.id))])
        ir_value.unlink()


class AccountInvoiceResCompany(models.Model):
    _inherit = 'res.company'

    capital_stock = fields.Float(string=u"Capital stock")


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def invoice_print(self):
        super(AccountInvoice, self).invoice_print()
        return self.env['report'].with_context(active_ids=self.ids).get_action(self, 'invoice.report.aeroo')
