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

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession
from openerp import models, fields, api, exceptions, _


@job(default_channel='root')
def job_invoice_ndp_contracts(session, contract_ids, context):
    """
    Job pour la facturation automatique des contrats.
    """
    session.env['ndp.analytic.contract'].with_context(context).browse(contract_ids).do_invoice_ndp_contract()
    return "End update"


class NdpAnalyticContract(models.Model):
    _name = 'ndp.analytic.contract'
    _inherits = {'account.analytic.account': 'analytic_account_id'}

    analytic_account_id = fields.Many2one('account.analytic.account',
                                          string=u"Analytic account",
                                          required=True,
                                          ondelete='cascade')
    sale_recurrence_line_ids = fields.One2many('ndp.sale.recurrence.line',
                                               'ndp_analytic_contract_id',
                                               string=u"Sale recurrence lines")
    consu_group_ids = fields.One2many('ndp.sale.consu.group', 'ndp_analytic_contract_id', string=u"consumption groups")
    sale_order_count = fields.Integer(u"# of sale orders", compute='_compute_counts')
    account_invoice_count = fields.Integer(u"# of invoices", compute='_compute_counts')

    @api.model
    def default_get(self, fields):
        res = super(NdpAnalyticContract, self).default_get(fields)
        res.update({'manager_id': self.env.user.id})
        return res

    @api.multi
    def _compute_counts(self):
        for rec in self:
            rec.sale_order_count = len(self.env['sale.order'].search([('project_id', '=', rec.analytic_account_id.id)]))
            rec.account_invoice_count = len(self.env['account.invoice'].search([
                '|',
                ('invoice_line.sale_recurrence_line_ids', 'ilike', self.sale_recurrence_line_ids.ids),
                ('invoice_line.sale_consu_line_ids', 'ilike', self.consu_group_ids.mapped('sale_consu_line_ids').ids)
            ]))

    @api.multi
    def open_billing_wizard(self):
        """
        Open a wizard to choose the order lines to bill among 'Sale', 'Recurrence' and 'Consumption'.
        """
        self.ensure_one()
        ctx = dict(self.env.context)
        ctx.update({'default_ndp_analytic_contract_id': self.id})
        return {
            'name': u"Billing %s" % self.name,
            'res_model': 'ndp.contract.billing.wizard',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def do_invoice_ndp_contract(self):
        """
        Facture les lignes récurrentes et de consommation du contrat dont la date de prochaine facturation a été
        dépassée.
        """
        self.ensure_one()
        today = datetime.date.today()
        current_month = today.month
        current_year = today.year
        sale_recurrence_lines = self.env['ndp.sale.recurrence.line'].search([
            ('ndp_analytic_contract_id', '=', self.id),
            ('true_nbdate', '<=', fields.Date.to_string(today)),
            ('auto_invoice', '=', True)
        ])
        sale_consu_lines = self.env['ndp.sale.consu.line'].search([
            ('ndp_analytic_contract_id', '=', self.id),
            ('billing_period_start', '<=', fields.Date.to_string(today)),
            ('auto_invoice', '=', True),
        ])

        wizard = self.env['ndp.contract.billing.wizard'].create({
            'ndp_analytic_contract_id': self.id,
            'billing_month': current_month,
            'billing_year': current_year,
            'sale_recurrence_line_ids': [(6, 0, sale_recurrence_lines.ids)],
            'sale_consu_line_ids': [(6, 0, sale_consu_lines.ids)],
        })

        wizard.with_context(cron_invoice_ndp_contracts=True).contract_create_invoice()

    @api.model
    def cron_invoice_ndp_contracts(self, jobify=True):
        """
        Cron pour lancer la facturation automatique des contrats (un par un).
        """
        contracts = self.env['ndp.analytic.contract'].search([('state', 'not in', ('draft', 'cancel'))])
        ctx = dict(self.env.context)
        ctx.update({'cron_invoice_ndp_contracts': True})
        if not jobify:
            for contract in contracts:
                self.do_invoice_ndp_contract(contract)
        else:
            for contract in contracts:
                job_invoice_ndp_contracts.delay(ConnectorSession.from_env(self.env), contract.ids, ctx)

    @api.multi
    def associated_sale_order(self):
        """
        Accède aux devis associés aux contrats
        """
        self.ensure_one()
        ctx = dict(self.env.context)
        ctx.update({'default_ndp_analytic_contract_id': self.id})
        return {
            'name': u"Sale orders",
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('project_id', '=', self.analytic_account_id.id)],
            'context': ctx,
        }

    @api.multi
    def associated_account_invoice(self):
        """
        Accède aux factures associées aux contrats
        """
        self.ensure_one()
        ctx = dict(self.env.context)
        ctx.update({'default_type': 'out_invoice', 'type': 'out_invoice', 'journal_type': 'sale'})
        tree_id = self.env.ref('account.invoice_tree').id
        form_id = self.env.ref('account.invoice_form').id
        return {
            'name': u"Invoices",
            'type': 'ir.actions.act_window',
            'res_model': 'account.invoice',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'target': 'current',
            'views': [(tree_id, 'tree'), (form_id, 'form')],
            'domain': [
                '|',
                ('invoice_line.sale_recurrence_line_ids', 'ilike', self.sale_recurrence_line_ids.ids),
                ('invoice_line.sale_consu_line_ids', 'ilike', self.consu_group_ids.mapped('sale_consu_line_ids').ids)
            ],
            'context': ctx,
        }

    @api.model
    def create(self, vals):
        """
        À la création d'un nouveau contrat, on lui crée des groupes de consommation pour chaque type de consommation.
        """
        res = super(NdpAnalyticContract, self).create(vals)

        for consu_type in self.env['ndp.consu.type'].search([]):
            self.env['ndp.sale.consu.group'].create({
                'ndp_analytic_contract_id': res.id,
                'consu_type_id': consu_type.id,
            })

        return res


class NdpAnalyticContractSaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_recurrence_line_ids = fields.One2many('ndp.sale.recurrence.line',
                                               'sale_id',
                                               string="Sale recurrence lines",
                                               copy=True)
    amount_annual_recurrence = fields.Float(u"Annual amount Exc.Taxes", compute='_compute_amount_annual_recurrence')
    ndp_contract_id = fields.Many2one('ndp.analytic.contract', string=u"Contrat", copy=False)
    project_id = fields.Many2one(related='ndp_contract_id.analytic_account_id')

    @api.multi
    @api.depends('sale_recurrence_line_ids',
                 'sale_recurrence_line_ids.date_start',
                 'sale_recurrence_line_ids.date_end',
                 'sale_recurrence_line_ids.price_unit',
                 'sale_recurrence_line_ids.recurrence_id',
                 'sale_recurrence_line_ids.product_uom_qty',
                 'sale_recurrence_line_ids.product_uom_id')
    def _compute_amount_annual_recurrence(self):
        for rec in self:
            amount = 0
            uom_temporality_year = self.env.ref('ndp_analytic_contract.ndp_uom_temporalite_year')
            for recurrence_line in rec.sale_recurrence_line_ids:
                if recurrence_line.product_uom_id.category_id == uom_temporality_year.category_id:
                    uom_in_year = self.env['product.uom']._compute_qty(
                        uom_temporality_year.id, 1, recurrence_line.product_uom_id.id)
                else:
                    uom_in_year = 12.0
                amount += uom_in_year * recurrence_line.price_unit * recurrence_line.product_uom_qty

            rec.amount_annual_recurrence = amount

    @api.multi
    def action_wait(self):
        """Surcharge pour pouvoir valider un devis même s'il ne contient que des lignes d'abonnements"""
        for rec in self:
            if not any(line.state != 'cancel' for line in rec.order_line) and not any(rec.sale_recurrence_line_ids):
                raise exceptions.except_orm(_('Error!'), _('You cannot confirm a sales order which has no line.'))
            noprod = rec.test_no_product(rec)
            if (rec.order_policy == 'manual') or noprod:
                rec.write({'state': 'manual', 'date_confirm': fields.Date.context_today(self)})
            else:
                self.write({'state': 'progress', 'date_confirm': fields.Date.context_today(self)})
            rec.mapped('order_line').filtered(lambda it: it.state != 'cancel').button_confirm()
        return True

    @api.multi
    def action_button_confirm(self):
        if all(product.type == 'service' for product in self.order_line.mapped('product_id')):
            self.order_policy = 'manual'
        result = super(NdpAnalyticContractSaleOrder, self).action_button_confirm()
        template = self.env.ref('nntech_ventes.modele_mail_notif_confirm_devis', False)
        if template:
            for rec in self:
                template.send_mail(rec.id, force_send=True)
        if not self.order_line and self.sale_recurrence_line_ids:
            self.write({'state': 'progress', 'manual_confirm': True})
            return result
        return result

    @api.multi
    def action_done(self):
        result = super(NdpAnalyticContractSaleOrder, self).action_done()
        if not self.order_line and self.sale_recurrence_line_ids:
            return result
        self.action_confirm_sale_order()
        return result

    @api.multi
    def action_confirm_sale_order(self):
        for rec in self:
            if rec.sale_recurrence_line_ids:
                rec.create_or_update_project_id()
                rec.write({
                    'state': 'done',
                })
            elif all(it.product_id.type == 'service' for it in rec.order_line):
                rec.write({
                    'state': 'done',
                })

    @api.multi
    def create_or_update_project_id(self):
        """
        La confirmation d'un devis entraîne la copie de ses lignes récurrentes dans le contrat associé.
        """
        self.ensure_one()
        contract = self.env['ndp.analytic.contract'].search([('analytic_account_id', '=', self.project_id.id)])
        if not contract:
            name = u"Contract : %s (%s)" % (self.partner_id.name, self.name)
            contract = self.env['ndp.analytic.contract'].create({
                'name': name,
                'partner_id': self.partner_id.id,
                'company_id': self.company_id.id,
                'manager_id': self.user_id.id,
            })

        for sr_line in self.sale_recurrence_line_ids:
            sr_line.copy({
                'sale_id': False,
                'ndp_analytic_contract_id': contract.id,
            })

        self.write({
            'manual_confirm': False,
            'ndp_contract_id': contract.id,
        })

        return contract


class NdpAnalyticContractAccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    sale_recurrence_line_ids = fields.Many2many('ndp.sale.recurrence.line', string=u"Sale recurrence lines")
    sale_consu_line_ids = fields.Many2many('ndp.sale.consu.line', string=u"Sale consumption lines")
