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

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class ProvisionAccountInvoice(models.Model):
    _inherit = 'account.invoice'

    is_provision_invoice = fields.Boolean(string=u"Is a provision invoice")
    reverse_invoice_date = fields.Date(string=u"Reverse invoice date")

    @api.multi
    @api.onchange('is_provision_invoice', 'date_invoice')
    def onchange_date_invoice(self):
        for rec in self:
            if rec.is_provision_invoice and rec.date_invoice:
                rec.reverse_invoice_date = (rec.date_invoice + relativedelta(months=1)).replace(day=1)

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        result = super(ProvisionAccountInvoice, self)._prepare_refund(invoice, date_invoice=date_invoice, date=date,
                                                                      description=description, journal_id=journal_id)
        result['is_provision_invoice'] = invoice.is_provision_invoice
        return result

    @api.model
    def cron_reverse_old_prevision_invoices(self):
        invoices_to_reverse = self.search([('state', '=', 'open'),
                                           ('is_provision_invoice', '=', True),
                                           ('reverse_invoice_date', '!=', False),
                                           ('reverse_invoice_date', '<=', fields.Date.today())])
        nb_invoices_to_reverse = len(invoices_to_reverse)
        index = 0
        for invoice in invoices_to_reverse:
            index += 1
            _logger.info(u"Reverse invoice %s (%s/%s)", invoice.number, index, nb_invoices_to_reverse)
            wizard = self.env['account.invoice.refund'].create({
                'description': _(u"Reverse invoice for provision invoice %s") % invoice.number,
                'date_invoice': invoice.date_invoice,
                'date': invoice.date_invoice,
                'filter_refund': 'cancel',
            })
            wizard.with_context(active_ids=invoice.ids).invoice_refund()


class ProvisionAccountInvoiceRefund(models.TransientModel):
    _inherit = 'account.invoice.refund'

    @api.multi
    def invoice_refund(self):
        active_ids = self.env.context.get('active_ids')
        existing_invoice_ids = self.env['account.invoice'].search([]).ids
        result = super(ProvisionAccountInvoiceRefund, self).invoice_refund()
        new_draft_invoices = self.env['account.invoice'].search([('id', 'not in', existing_invoice_ids),
                                                                 ('state', '=', 'draft')])
        if len(active_ids) == 1 and self.filter_refund == 'modify':
            initial_invoice = self.env['account.invoice'].browse(active_ids)
            new_draft_invoices.write({'is_provision_invoice': initial_invoice.is_provision_invoice,
                                      'date_invoice': initial_invoice.date_invoice,
                                      'reverse_invoice_date': initial_invoice.reverse_invoice_date})
        return result
