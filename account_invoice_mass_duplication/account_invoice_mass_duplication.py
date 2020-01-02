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

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class MassDuplicationAccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def mass_duplicate(self):
        return {
            'name': _(u"Duplication"),
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'wizard.invoice.mass.duplication',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': dict(self.env.context),
        }


class WizardInvoiceMassDuplication(models.TransientModel):
    _name = 'wizard.invoice.mass.duplication'
    _description = "Wizard for massive duplication of invoices"

    date = fields.Date(string=u"Date of new invoices", required=True, default=fields.Date.today)

    @api.multi
    def duplicate(self):
        self.ensure_one()
        invoices = self.env['account.invoice'].browse(self.env.context.get('active_ids', []))
        duplicated_invoices = self.env['account.invoice']
        for invoice in invoices:
            _logger.info(u"Duplicate invoice ID=%s (number %s)", invoice.id, invoice.number)
            duplicated_invoices += invoice.copy({'date_invoice': self.date})
        return duplicated_invoices
