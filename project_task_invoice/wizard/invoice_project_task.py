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

from odoo import fields, models, api, _ as _t
from odoo.exceptions import UserError


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
