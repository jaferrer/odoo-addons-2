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

from odoo import api, models, fields

INV_TYPE_MAP = {
    'out_invoice': 'income',
    'out_refund': 'income',
    'in_invoice': 'expense',
    'in_refund': 'expense',
}


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    account_analytic_id = fields.Many2one('account.analytic.account')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(AccountInvoiceLine, self)._onchange_product_id()
        inv_type = self.invoice_id.type
        ana_account = self.env['account.analytic.account']
        if self.product_id:
            ana_accounts = self.product_id.product_tmpl_id._get_product_analytic_accounts()
            ana_account = ana_accounts[INV_TYPE_MAP[inv_type]]
        if not ana_account:
            ana_accounts = self.invoice_id.partner_id._get_partner_analytic_accounts()
            ana_account = ana_accounts.get(INV_TYPE_MAP[inv_type], self.env['account.analytic.account'])
            self.account_analytic_id = ana_account.id
        return res

    @api.model
    def create(self, vals):
        invoice_id = vals.get('invoice_id')
        if invoice_id and not vals.get('account_analytic_id'):
            invoice = self.env['account.invoice'].browse(invoice_id)
            inv_type = invoice.type
            ana_accounts = invoice.partner_id.partner_id._get_partner_analytic_accounts()
            ana_account = ana_accounts.get(INV_TYPE_MAP[inv_type], self.env['account.analytic.account'])
            vals['account_analytic_id'] = ana_account.id
        return super(AccountInvoiceLine, self).create(vals)
