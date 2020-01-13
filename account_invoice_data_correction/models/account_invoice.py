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

from odoo import models, api, exceptions, _


class AccountInvoiceDataCorrection(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def change_type_for_draft_invoices(self):
        return {
            'name': _(u"Change invoices types"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice.change.type',
            'target': 'new',
            'context': dict(self.env.context),
        }

    @api.multi
    def change_number_or_date_for_validated_invoices(self):
        invoices = self.env['account.invoice'].browse(self.env.context.get('active_ids', []))
        if any([rec.state not in ['open', 'paid'] for rec in invoices]):
            raise exceptions.UserError(_(u"This operation is allowed only on open or paid invoices"))
        if len(invoices) != 1:
            raise exceptions.UserError(_(u"Please process invoices one by one"))
        wizard = self.env['account.invoice.change.date.number'].create({'invoice_id': invoices.id})
        return {
            'name': _(u"Change invoices dates or numbers"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice.change.date.number',
            'res_id': wizard.id,
            'target': 'new',
            'context': dict(self.env.context),
        }

    @api.multi
    def define_number_and_confirm(self):
        invoices = self.env['account.invoice'].browse(self.env.context.get('active_ids', []))
        if len(invoices) != 1:
            raise exceptions.UserError(_(u"Please process invoices one by one"))
        if invoices.state != 'draft':
            raise exceptions.UserError(_(u"This operation is allowed only on draft invoices"))
        wizard = self.env['account.invoice.confirm.set.number'].create({'invoice_id': invoices.id})
        return {
            'name': _(u"Define Invoice Numbers And Confirm"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice.confirm.set.number',
            'res_id': wizard.id,
            'target': 'new',
            'context': dict(self.env.context),
        }
