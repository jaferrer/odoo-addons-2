# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import fields, models, api, _ as _t
from odoo.exceptions import UserError
from odoo.tools import float_compare


class ProjectProject(models.Model):
    _inherit = 'project.project'

    @api.multi
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
        if not journal_id:
            raise UserError(_t('Please define an accounting sale journal for this company.'))
        invoice_vals = {
            'origin': self.name,
            'type': 'out_invoice',
            'account_id': self.partner_id.property_account_receivable_id.id,
            'partner_id': self.partner_id.id,
            'partner_shipping_id': self.partner_id.id,
            'journal_id': journal_id,
            'user_id': self.env.user.id,
        }
        return invoice_vals


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    is_delivered = fields.Boolean(u"Is Delivered")


class ProjectTaskInvoice(models.Model):
    _inherit = 'project.task'

    time_spent = fields.Float(u"Time sold")
    date_invoiced = fields.Date(u"Invoice Date")
    date_delivered = fields.Date(u"Date delivered", track_visibility='onchange', readonly=True)
    project_partner_id = fields.Many2one(
        'res.partner',
        u"Client du projet",
        related='project_id.partner_id',
        readonly=True
    )
    initial_sale_line_id = fields.Many2one(
        'sale.order.line',
        u"Sale Order Line",
        domain=[('order_id.state', '!=', 'cancel')]
    )
    product_to_invoice_id = fields.Many2one('product.product', u"Product To Invoice")
    price = fields.Float(u"Price of this task", compute='_compute_task_price')
    initial_sale_id = fields.Many2one('sale.order', u"Sale Order")
    stage_is_delivered = fields.Boolean(u"Is Delivered", related='stage_id.is_delivered', store=True)

    @api.onchange('initial_sale_line_id')
    def _onchange_initial_sale_line_id(self):
        self.initial_sale_id = self.initial_sale_line_id.order_id

    @api.onchange('initial_sale_id')
    def _onchange_initial_sale_id(self):
        if self.initial_sale_line_id.order_id != self.initial_sale_id:
            self.initial_sale_line_id = False

    @api.multi
    @api.depends('initial_sale_line_id', 'product_to_invoice_id')
    def _compute_task_price(self):
        for rec in self:
            if rec.initial_sale_line_id:
                rec.price = rec.initial_sale_line_id.price_unit * rec.time_spent
            elif rec.product_to_invoice_id:
                rec.price = rec.product_to_invoice_id.with_context(
                    partner_id=self.project_partner_id.id,
                    pricelist=self.project_partner_id.property_product_pricelist.id
                ).price * rec.time_spent
            else:
                rec.price = 0

    @api.multi
    def action_mark_as_delivered(self):
        for rec in self:
            if rec.initial_sale_line_id:
                rec.initial_sale_line_id.qty_delivered += rec.time_spent
            if not rec.date_delivered:
                rec.date_delivered = fields.Date.today()

    @api.multi
    def action_cancel_delivery(self):
        for rec in self:
            if rec.initial_sale_line_id:
                rec.initial_sale_line_id.qty_delivered -= rec.time_spent
            rec.date_delivered = False

    @api.multi
    def invoice_project_task(self):
        if any(not rec.project_partner_id for rec in self):
            raise UserError(_t(u"You can't create an invoice from a task if the task's customer isn't filled"))
        if len(self.mapped('project_partner_id')) > 1:
            raise UserError(_t(u"You can't create an invoice for several customers"))
        return {
            'type': 'ir.actions.act_window',
            'name': 'To Invoice Tasks',
            'res_model': 'invoice.project.task.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context),
        }

    @api.multi
    def _prepare_invoice_line(self, qty=None):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        """
        self.ensure_one()
        res = {}
        product = self.env.ref('project_task_invoice.ndp_product_product_other')
        account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
        if not account:
            raise UserError(
                _t('Please define income account for this product: "%s" (id:%d) - or for its category: "%s".') %
                (product.name, product.id, product.categ_id.name))

        res = {
            'name': self.name,
            'sequence': self.sequence,
            'origin': self.name,
            'account_id': account.id,
            'price_unit': product.with_context(
                partner_id=self.project_partner_id.id,
                pricelist=self.project_partner_id.property_product_pricelist.id
            ).price,
            'quantity': qty or self.time_spent,
            'uom_id': product.uom_id.id,
            'product_id': product.id,
            'invoice_line_tax_ids': [(6, 0, product.taxes_id.ids)],
            'account_analytic_id': self.project_id.analytic_account_id.id,
        }
        return res


class ProjectTaskInvoiceSaleOrder(models.Model):
    _inherit = 'sale.order'

    wrong_line_tasks_qty = fields.Boolean(u"Check Qty", compute='_compute_is_lines_qty_equal_tasks_qty')

    @api.multi
    def _compute_is_lines_qty_equal_tasks_qty(self):
        for rec in self:
            rec.wrong_line_tasks_qty = any(line.wrong_task_qty for line in rec.order_line)

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        res = super(ProjectTaskInvoiceSaleOrder, self).action_invoice_create(grouped=grouped, final=final)

        # Valorisation de la date de facturation des tâches liées au lignes facturées
        invoices = self.env['account.invoice'].search([('id', '=', res[0])])
        date_invoice = invoices[0].date
        if not date_invoice:
            date_invoice = fields.Date.today()
        for invoice in invoices:
            for invoice_line in invoice.invoice_line_ids:
                for sale_line in invoice_line.sale_line_ids:
                    tasks = self.env['project.task'].search([('initial_sale_line_id', '=', sale_line.id)])
                    tasks.write({'date_invoiced': date_invoice})

        return res


class ProjectTaskInvoiceSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    wrong_task_qty = fields.Boolean(u"Check Qty", compute='_compute_is_self_qty_equal_tasks_qty')
    initial_task_ids = fields.One2many(
        'project.task',
        'initial_sale_line_id',
        u"Tâches initiales",
        readonly=True
    )
    initial_tasks_amount = fields.Float(u"Amount Task", compute='_compute_initial_tasks_amount')

    @api.multi
    def _compute_initial_tasks_amount(self):
        for rec in self:
            rec.initial_tasks_amount = sum(rec.initial_task_ids.mapped('time_spent'))

    @api.multi
    def _compute_is_self_qty_equal_tasks_qty(self):
        for rec in self:
            sum_time_spent = sum(rec.initial_task_ids.mapped('time_spent'))
            compare = float_compare(rec.product_uom_qty, sum_time_spent, precision_digits=2)
            rec.wrong_task_qty = (rec.state not in ['draft', 'cancel', 'done'] and rec.initial_task_ids and compare)


class InvoiceProjectTask(models.TransientModel):
    _name = 'invoice.project.task.wizard'

    date_invoiced = fields.Date(u"Billing Date", default=fields.Date.context_today)
    has_new_date = fields.Boolean(u"Overwrite Billing Date in Tasks", default=True)
    mark_task_as_delivered = fields.Boolean(u"Set Task as delivered", default=True)
    task_ids = fields.Many2many('project.task', string=u"Tasks to Invoice",
                                default=lambda self: self.env.context.get('active_ids', []))

    @api.multi
    def to_invoice_tasks(self):
        if any(not task.project_id.partner_id for task in self.task_ids):
            raise UserError(_t(u"You can't create an invoice from a task if the task's customer isn't filled"))
        sale_orders = self.task_ids.mapped('initial_sale_id')
        if any(sale.state in ['draft', 'done', 'cancel'] for sale in sale_orders):
            raise UserError(_t(u"You can only invoice confirmed Sale Order"))

        if self.has_new_date:
            self.task_ids.write({'date_invoiced': self.date_invoiced})
        if self.mark_task_as_delivered:
            self.task_ids.action_mark_as_delivered()

        invoice_ids = []
        task_with_sale_lines = self.task_ids.mapped('initial_sale_line_id.order_id')
        if task_with_sale_lines:
            invoice_ids = task_with_sale_lines.action_invoice_create(grouped=True)

        task_wo_sale_lines = self.task_ids.filtered(lambda it: not it.initial_sale_line_id)
        partner_invoice = {}
        if task_wo_sale_lines:
            for task_wo_sale_line in task_wo_sale_lines:
                invoice_id = partner_invoice.get(task_wo_sale_line.project_id.partner_id)
                if not invoice_id:
                    invoice = self.env['account.invoice'].create(task_wo_sale_line.project_id._prepare_invoice())
                    invoice._onchange_partner_id()
                    invoice_id = invoice.id
                    partner_invoice[task_wo_sale_line.project_id.partner_id] = invoice_id

                data = task_wo_sale_line._prepare_invoice_line()
                data['invoice_id'] = invoice_id
                self.env['account.invoice.line'].create(data)
        invoice_ids.extend(partner_invoice.values())
        self.env['account.invoice'].browse(invoice_ids).compute_taxes()
        return self._get_result_action(invoice_ids)

    @api.model
    def _get_result_action(self, invoice_ids):
        result = {
            'type': 'ir.actions.act_window',
            'name': _t(u"Invoices"),
            'res_model': 'account.invoice',
            'target': 'current',
            'context': self.env.context,
        }
        if len(invoice_ids) != 1:
            result['views'] = [
                (self.env.ref('account.invoice_tree').id, 'tree'),
                (self.env.ref('account.invoice_form').id, 'form')
            ]
            result['domain'] = [('id', 'in', invoice_ids)]
        else:
            result['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
            result['res_id'] = invoice_ids[0]
        return result
