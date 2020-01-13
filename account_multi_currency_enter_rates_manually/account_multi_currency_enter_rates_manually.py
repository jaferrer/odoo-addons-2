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

from odoo import models, fields, api, exceptions, _


class EnterRateAccountInvoice(models.Model):
    _inherit = 'account.invoice'

    same_currency_as_company = fields.Boolean(string=u"Same currency as the company",
                                              compute='_compute_same_currency_as_company')

    @api.multi
    @api.depends('currency_id', 'company_id', 'company_id.currency_id')
    def _compute_same_currency_as_company(self):
        for rec in self:
            rec.same_currency_as_company = rec.currency_id == rec.company_id.currency_id

    @api.multi
    def enter_rate_and_validate(self):
        self.ensure_one()
        if self.state != 'draft':
            raise exceptions.UserError(_(u"This action is allowed only on draft invoices"))
        ctx = dict(self.env.context)
        ctx['default_invoice_id'] = self.id
        ctx['default_description'] = _(u"Help: 1.00 %s = <Rate> %s") % (self.company_id.currency_id.name,
                                                                        self.currency_id.name)
        ctx['default_rate'] = self.currency_id.with_context(date=self.date_invoice).rate
        return {
            'name': _(u"Validate invoice"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'account.invoice.enter.rate',
            'context': ctx,
        }


class EnterRateAccountPayment(models.Model):
    _inherit = 'account.payment'

    same_currency_as_company = fields.Boolean(string=u"Same currency as the company",
                                              compute='_compute_same_currency_as_company')
    rate = fields.Float(string=u"Rate", digits=(12, 6))

    @api.multi
    @api.depends('currency_id', 'company_id', 'company_id.currency_id')
    def _compute_same_currency_as_company(self):
        for rec in self:
            rec.same_currency_as_company = rec.currency_id == rec.company_id.currency_id

    @api.onchange('payment_date', 'currency_id', 'company_id')
    def _onchange_payment_date(self):
        self.ensure_one()
        if self.payment_date and self.currency_id:
            self.rate = self.currency_id.with_context(date=self.payment_date).rate

    @api.multi
    def action_validate_invoice_payment(self):
        for rec in self:
            if not rec.same_currency_as_company and rec.payment_date:
                rate = self.env['res.currency.rate'].sudo().search([('currency_id', '=', rec.currency_id.id),
                                                                    ('name', '=', rec.payment_date),
                                                                    ('company_id', '=', rec.company_id.id)])
                if rate:
                    rate.write({'rate': rec.rate})
                else:
                    self.env['res.currency.rate'].sudo().create({
                        'currency_id': rec.currency_id.id,
                        'company_id': rec.company_id.id,
                        'name': rec.payment_date,
                        'rate': rec.rate
                    })
        return super(EnterRateAccountPayment, self).action_validate_invoice_payment()


class AccountInvoiceValidationEnterRate(models.TransientModel):
    _name = 'account.invoice.enter.rate'
    _description = u"Wizard to enter manually currency rates while validating an invoice"

    invoice_id = fields.Many2one('account.invoice', string=u"Invoice")
    description = fields.Char(string=u"Description", readonly=True)
    rate = fields.Float(string=u"Rate", digits=(12, 6), required=True)

    @api.multi
    def enter_rate_and_validate(self):
        self.ensure_one()
        if self.rate:
            rate = self.env['res.currency.rate'].sudo().search([('currency_id', '=', self.invoice_id.currency_id.id),
                                                                ('name', '=', self.invoice_id.date_invoice),
                                                                ('company_id', '=', self.invoice_id.company_id.id)])
            if rate:
                rate.write({'rate': self.rate})
            else:
                self.env['res.currency.rate'].sudo().create({
                    'currency_id': self.invoice_id.currency_id.id,
                    'company_id': self.invoice_id.company_id.id,
                    'name': self.invoice_id.date_invoice,
                    'rate': self.rate
                })
        self.invoice_id.action_invoice_open()
