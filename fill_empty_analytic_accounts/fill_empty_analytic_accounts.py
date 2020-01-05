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

import logging

from odoo import models, api, fields

_logger = logging.getLogger(__name__)


class AccountInvoiceLineFillAnalyticAccount(models.Model):
    _inherit = 'account.invoice.line'

    account_analytic_id = fields.Many2one('account.analytic.account')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(AccountInvoiceLineFillAnalyticAccount, self)._onchange_product_id()
        if not self.account_analytic_id:
            self.fill_empty_account_analytic_for_lines()
        return res

    @api.multi
    def fill_empty_account_analytic_for_lines(self, logs=False):
        for line in self:
            analytic_account = self.env['account.analytic.account']
            if line.invoice_id.type in ['out_invoice', 'out_refund']:
                analytic_account = self.env.ref('fill_empty_analytic_accounts.analytic_account_sales')
            if line.invoice_id.type in ['in_invoice', 'in_refund']:
                analytic_account = self.env.ref('fill_empty_analytic_accounts.analytic_account_purchases')
            if logs:
                _logger.info(u"Account invoice line ID=%s attached to analytic account %s",
                             line.id, analytic_account.id)
            if analytic_account:
                line.account_analytic_id = analytic_account

    @api.model
    def fill_empty_account_analytic_ids(self):
        for line in self.env['account.invoice.line'].search([('account_analytic_id', '=', False)]):
            line.fill_empty_account_analytic_for_lines(logs=True)

    @api.model
    def create(self, vals):
        if vals.get('account_analytic_id'):
            return super(AccountInvoiceLineFillAnalyticAccount, self).create(vals)
        invoice_id = vals.get('invoice_id')
        if invoice_id:
            invoice = self.env['account.invoice'].browse(invoice_id)
            if invoice.type in ['out_invoice', 'out_refund']:
                vals['account_analytic_id'] = self.env.ref('fill_empty_analytic_accounts.analytic_account_sales').id
            if invoice.type in ['in_invoice', 'in_refund']:
                vals['account_analytic_id'] = self.env.ref('fill_empty_analytic_accounts.analytic_account_purchases').id
        return super(AccountInvoiceLineFillAnalyticAccount, self).create(vals)
