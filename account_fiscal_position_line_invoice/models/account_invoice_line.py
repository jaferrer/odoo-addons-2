# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    account_fiscal_position_id = fields.Many2one('account.fiscal.position',
                                                 string=u"Position fiscale",
                                                 default=lambda self: self.invoice_id.fiscal_position_id)

    @api.multi
    def get_invoice_line_account(self, type, product, fpos, company):
        if self and self.invoice_type in ('out_invoice', 'out_refund'):
            fpos = self.account_fiscal_position_id
        return super(AccountInvoiceLine, self).get_invoice_line_account(type, product, fpos, company)

    @api.multi
    def fpos_tax_account_mapping(self):
        self.ensure_one()
        taxes = self.product_id.taxes_id or self.account_id.tax_ids
        invoice_line_tax = self.account_fiscal_position_id.map_tax(taxes,
                                                                   self.product_id,
                                                                   self.invoice_id.partner_id)
        account = self.get_invoice_line_account(self.invoice_id.type,
                                                self.product_id,
                                                self.account_fiscal_position_id,
                                                self.invoice_id.company_id)
        return {'invoice_line_tax_ids': [(6, 0, invoice_line_tax[0].ids)], 'account_id': account.id}

    @api.multi
    def write(self, vals):
        if 'account_fiscal_position_id' in vals:
            vals.update(self.fpos_tax_account_mapping())
        return super(AccountInvoiceLine, self).write(vals)

    @api.onchange('account_fiscal_position_id')
    def _onchange_fiscal_position_id(self):
        values = self.fpos_tax_account_mapping()
        self.invoice_line_tax_ids = values['invoice_line_tax_ids']
        self.account_id = values['account_id']

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.account_fiscal_position_id = self.invoice_id.fiscal_position_id
        return super(AccountInvoiceLine, self)._onchange_product_id()
