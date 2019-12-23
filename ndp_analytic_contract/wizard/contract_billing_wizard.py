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
import datetime

from dateutil import relativedelta

from openerp import models, fields, api, exceptions, _


class NdpAnalyticContractBillingWizard(models.TransientModel):
    _name = 'ndp.contract.billing.wizard'

    ndp_analytic_contract_id = fields.Many2one('ndp.analytic.contract', string=u"Contract")
    billing_month = fields.Selection([(1, u"January"),
                                      (2, u"February"),
                                      (3, u"March"),
                                      (4, u"April"),
                                      (5, u"May"),
                                      (6, u"June"),
                                      (7, u"July"),
                                      (8, u"August"),
                                      (9, u"September"),
                                      (10, u"October"),
                                      (11, u"November"),
                                      (12, u"December")],
                                     string=u"Month")
    billing_year = fields.Integer(u"Year")
    all_lines = fields.Boolean(u"All lines", default=True)
    all_types = fields.Boolean(u"All types")
    so_lines = fields.Boolean(u"Sale")
    sr_lines = fields.Boolean(u"Recurrence")
    sc_lines = fields.Boolean(u"Consumption")
    sale_recurrence_line_ids = fields.Many2many('ndp.sale.recurrence.line', string="Sale recurrence lines")
    sale_consu_line_ids = fields.Many2many('ndp.sale.consu.line', string="Sale consumption lines")

    @api.model
    def default_get(self, fields_bis):
        res = super(NdpAnalyticContractBillingWizard, self).default_get(fields_bis)

        today = datetime.date.today()
        default_month = today.month
        default_year = today.year
        res.update({
            'billing_month': default_month,
            'billing_year': default_year,
        })

        return res

    @api.multi
    @api.onchange('all_lines')
    def _onchange_all_lines(self):
        self.ensure_one()
        if self.all_lines:
            self.sale_recurrence_line_ids = self.ndp_analytic_contract_id.sale_recurrence_line_ids
            self.sale_consu_line_ids = self.ndp_analytic_contract_id.consu_group_ids.mapped('sale_consu_line_ids')
        else:
            self.sale_recurrence_line_ids = self.env['ndp.sale.recurrence.line']
            self.sale_consu_line_ids = self.env['ndp.sale.consu.line']

    @api.multi
    @api.onchange('all_types')
    def _onchange_all_types(self):
        self.ensure_one()
        self.so_lines = self.sr_lines = self.sc_lines = self.all_types

    @api.multi
    def contract_create_invoice(self):
        """
        Lance la création d'une facture et lui associe les lignes de vente/récurrence/conso sélectionnées dans le
        contrat.
        """
        self.ensure_one()
        new_invoice = self.env['account.invoice'].create({
            'name': self.ndp_analytic_contract_id.name,
            'origin': self.ndp_analytic_contract_id.name,
            'state': 'draft',
            'type': 'out_invoice',
            'reference': False,
            'account_id': self.ndp_analytic_contract_id.partner_id.property_account_receivable.id,
            'partner_id': self.ndp_analytic_contract_id.partner_id.id,
            'company_id': self.ndp_analytic_contract_id.manager_id.company_id.id,
            'user_id': self.ndp_analytic_contract_id.manager_id.id,
        })

        wizard_date = datetime.date(self.billing_year, self.billing_month, 1) + relativedelta.relativedelta(day=31)
        # Lignes de récurrence
        for invoice_line_vals in self.sale_recurrence_line_ids.bill_recurrence_lines(new_invoice, wizard_date):
            self.env['account.invoice.line'].create(invoice_line_vals)

        # Lignes de consommation
        for invoice_line_vals in self.sale_consu_line_ids.bill_consumption_lines(new_invoice, wizard_date):
            self.env['account.invoice.line'].create(invoice_line_vals)

        # S'il n'y a rien à facturer dans la période sélectionnée
        if not new_invoice.invoice_line:
            return _(u"There is nothing to invoice during this period %s-%s." % (self.billing_month, self.billing_year))

        form_id = self.env.ref('account.invoice_form').id
        return {
            'name': u"Invoice",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'res_id': new_invoice.id,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
        }
