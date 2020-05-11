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

from odoo import fields, models, api
from odoo.exceptions import UserError


class ProjectTaskInvoice(models.Model):
    _inherit = 'project.task'

    time_spent = fields.Float(u"Time sold")
    date_invoiced = fields.Date(u"Invoice Date")
    project_partner_id = fields.Many2one(
        'res.partner',
        u"Client du projet",
        related='project_id.partner_id',
        readonly=True
    )
    initial_sale_line_id = fields.Many2one(
        'sale.order.line',
        u"Sale order line",
        domain=[('order_id.state', '!=', 'cancel')]
    )
    initial_sale_id = fields.Many2one('sale.order', u"Sale order")

    @api.onchange('initial_sale_line_id')
    def _onchange_initial_sale_line_id(self):
        self.initial_sale_id = self.initial_sale_line_id.order_id

    @api.onchange('initial_sale_id')
    def _onchange_initial_sale_id(self):
        if self.initial_sale_line_id.order_id != self.initial_sale_id:
            self.initial_sale_line_id = False

    @api.multi
    def invoice_project_task(self):
        ctx = dict(self.env.context)
        ctx.update({'default_task_ids': self.env.context.get('active_ids')})
        if any(not rec.partner_id for rec in self):
            raise UserError(u"You can't create an invoice from a task if the task's customer isn't filled")
        if len(self.mapped('partner_id')) > 1:
            raise UserError(u"You can't create an invoice for several customers")
        return {
            'type': 'ir.actions.act_window',
            'name': 'To Invoice Tasks',
            'res_model': 'invoice.project.task.wizard',
            'views': [(False, 'form')],
            'target': 'new',
            'context': ctx,
        }


class InvoiceProjectTask(models.TransientModel):
    _name = 'invoice.project.task.wizard'

    date_invoiced = fields.Date(u"Billing Date", default=fields.Date.today())
    has_new_date = fields.Boolean(u"Overwrite Billing Date in Tasks", default=True)
    task_ids = fields.Many2many('project.task', string=u"Tasks to Invoice")

    @api.multi
    def create_invoice_lines_from_tasks(self, tasks):
        res = self.env['account.invoice.line']
        product = self.env.ref('project_task_invoice.ndp_product_product_other')
        vals = {
            'product_id': product.id,
            'name': product.name,
            'price_unit': product.list_price,
            'account_id': self.env.ref('l10n_fr.1_fr_pcg_recv').id,
        }
        for task in tasks:
            vals.update({'quantity': task.time_spent or task.planned_days})
            res |= self.env['account.invoice.line'].create(vals)
        return res

    @api.multi
    def create_invoice_lines_from_order_lines(self, order_lines):
        res = self.env['account.invoice.line']
        vals = {'account_id': self.env.ref('l10n_fr.1_fr_pcg_recv').id}
        for order_line in order_lines:
            vals.update({
                'product_id': order_line.product_id.id,
                'name': order_line.product_id.name,
                'quantity': order_line.product_uom_qty,
                'price_unit': order_line.price_unit,
            })
            res |= self.env['account.invoice.line'].create(vals)
        return res

    @api.multi
    def prepare_invoice_lines(self):
        self.ensure_one()
        res = self.env['account.invoice.line']
        tasks_wo_sol = self.env['project.task']  # tasks without sale order line
        order_lines = self.env['sale.order.line']
        for task in self.task_ids:
            if task.initial_sale_line_id:
                order_lines |= task.initial_sale_line_id
            else:
                tasks_wo_sol |= task
        res |= self.create_invoice_lines_from_order_lines(order_lines)
        res |= self.create_invoice_lines_from_tasks(tasks_wo_sol)
        return res

    @api.multi
    def to_invoice_tasks(self):
        if self.has_new_date:
            self.task_ids.write({'date_invoiced': self.date_invoiced})

        if any(not task.partner_id for task in self.task_ids):
            raise UserError(u"You can't create an invoice from a task if the task's customer isn't filled")
        partner = self.task_ids.mapped('partner_id')
        if len(partner) > 1:
            raise UserError(u"You can't create one invoice for several customers")

        vals = {
            'date_invoice': self.date_invoiced,
            'partner_id': partner.id,
            'account_id': self.env.ref('l10n_fr.1_fr_pcg_recv').id,
            'invoice_line_ids': [(6, 0, self.prepare_invoice_lines().ids)],
        }
        invoice = self.env['account.invoice'].create(vals)
        orders = self.task_ids.mapped('initial_sale_id')
        orders.write({'invoice_ids': [(4, invoice.id, 0)]})
        return {
            'type': 'ir.actions.act_window',
            'name': invoice.name,
            'res_model': 'account.invoice',
            'res_id': invoice.id,
            'views': [(self.env.ref('account.invoice_form').id, 'form')],
            'target': 'current',
            'context': self.env.context,
        }
