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

from odoo import models, fields, api


class AccountInvoiceResCompany(models.Model):
    _inherit = 'res.company'

    capital_stock = fields.Float(string=u"Capital stock")


class AccountInvoiceDeleteReport(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def link_report_with_mail(self):
        """
        Replace the Odoo report by the aeroo report in the 'Send by mail' button of the form view.
        """
        mail_model = self.env.ref('account.email_template_edi_invoice')
        report = self.env.ref(self._get_report_id())
        mail_model.report_template = report.id

    @api.model
    def _get_report_id(self):
        return 'account_invoice_report_aeroo.account_invoice_report_aeroo'

    @api.model
    def hide_odoo_report(self):
        """
        Get rid of the Odoo reports in the list of the 'Print' action.
        """
        odoo_sale_order_report_invoice = self.env.ref('account.account_invoices')
        odoo_sale_order_report_invoice_with_no_payment = self.env.ref('account.account_invoices_without_payment')
        self.env['ir.actions.report'].browse(odoo_sale_order_report_invoice.id).unlink_action()
        self.env['ir.actions.report'].browse(odoo_sale_order_report_invoice_with_no_payment.id).unlink_action()


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def invoice_print(self):
        """
        Replace the Odoo report form view by the aeroo report in the 'Print' button of the form view.
        """
        super(AccountInvoice, self).invoice_print()
        return self.env.ref('account_invoice_report_aeroo.account_invoice_report_aeroo').read()[0]
