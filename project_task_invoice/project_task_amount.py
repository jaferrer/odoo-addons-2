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
    def to_invoice_tasks(self):
        if self.has_new_date:
            self.task_ids.write({'date_invoiced': self.date_invoiced})
