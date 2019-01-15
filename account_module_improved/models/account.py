# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def pay_and_reconcile(self, pay_journal, pay_amount=None, date=None, writeoff_acc=None):
        """ Override of the method  pay_and_reconcile form accout/account_invoice.py#1081

        Create and post an account.payment for the invoice self,
         which creates a journal entry that reconciles the invoice.

            :param pay_journal: journal in which the payment entry will be created
            :param pay_amount: amount of the payment to register, defaults to the residual of the invoice
            :param date: payment date, defaults to fields.Date.context_today(self)
            :param writeoff_acc: account in which to create a writeoff if pay_amount < self.residual,
            so that the invoice is fully paid
        """
        assert len(self) == 1, "Can only pay one invoice at a time."
        if isinstance(pay_journal, (int, long)):
            pay_journal = self.env['account.journal'].browse([pay_journal])
        self._create_payment_and_reconcile(pay_journal=pay_journal,
                                           pay_amount=pay_amount,
                                           date=date,
                                           writeoff_acc=writeoff_acc)
        return True

    @api.multi
    def _create_payment_and_reconcile(self, pay_journal, pay_amount=None, date=None, writeoff_acc=None):
        payment = self._create_payment(pay_journal, pay_amount, date, writeoff_acc)
        payment._after_payment_created_for_reconcile()
        return payment

    def _create_payment(self, pay_journal, pay_amount=None, date=None, writeoff_acc=None):
        self.ensure_one()
        payment_type = self.type in ('out_invoice', 'in_refund') and 'inbound' or 'outbound'
        payment_method = self._get_default_payment_method(payment_type)
        journal_payment_methods = pay_journal._get_default_journal_payment_method(payment_type)
        if payment_method not in journal_payment_methods:
            raise UserError(_('No appropriate payment method enabled on journal %s') % pay_journal.name)
        communication = self.type in ('in_invoice', 'in_refund') and self.reference or self.number
        if self.origin:
            communication = '%s (%s)' % (communication, self.origin)
        payment_vals = self._get_data_payment(communication,
                                              date,
                                              pay_amount,
                                              pay_journal,
                                              payment_method,
                                              payment_type,
                                              writeoff_acc)
        if self.env.context.get('tx_currency_id'):
            payment_vals['currency_id'] = self.env.context.get('tx_currency_id')
        payment = self.env['account.payment'].create(payment_vals)
        return payment

    @api.multi
    def _get_data_payment(self, communication, date, pay_amount, pay_journal, payment_method, payment_type,
                          writeoff_acc):
        self.ensure_one()
        return {
            'invoice_ids': [(6, 0, self.ids)],
            'amount': pay_amount or self.residual,
            'payment_date': date or fields.Date.context_today(self),
            'communication': communication,
            'partner_id': self.partner_id.id,
            'partner_type': self.type in ('out_invoice', 'out_refund') and 'customer' or 'supplier',
            'journal_id': pay_journal.id,
            'payment_type': payment_type,
            'payment_method_id': payment_method.id,
            'payment_difference_handling': writeoff_acc and 'reconcile' or 'open',
            'writeoff_account_id': writeoff_acc and writeoff_acc.id or False,
        }

    @api.model
    def _get_default_payment_method(self, payment_type):
        if payment_type == 'inbound':
            return self.env.ref('account.account_payment_method_manual_in')
        return self.env.ref('account.account_payment_method_manual_out')


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.multi
    def _get_default_journal_payment_method(self, payment_type):
        self.ensure_one()
        if payment_type == 'inbound':
            return self.inbound_payment_method_ids
        return self.outbound_payment_method_ids


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.multi
    def _after_payment_created_for_reconcile(self):
        self.ensure_one().post()
