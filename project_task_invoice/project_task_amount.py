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
    date_delivered = fields.Date(u"Date delivered", track_visibility='onchange')
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
    def action_mark_as_delivered(self):
        for rec in self:
            if not rec.initial_sale_id:
                raise UserError(u"The task {} has no linked order.".format(rec.name))
            if not rec.initial_sale_line_id:
                raise UserError(u"The task {} has the linked order {}, but has no linked order line."
                                u"".format(rec.name, rec.initial_sale_id.name))
            rec.date_delivered = rec.initial_sale_id and rec.initial_sale_id.date_order
            rec.initial_sale_line_id.qty_delivered = rec.time_spent

    @api.multi
    def action_cancel_delivery(self):
        for rec in self:
            if not rec.initial_sale_id:
                raise UserError(u"The task {} has no linked order.".format(rec.name))
            if not rec.initial_sale_line_id:
                raise UserError(u"The task {} has the linked order {}, but has no linked order line."
                                u"".format(rec.name, rec.initial_sale_id.name))
            rec.date_delivered, rec.initial_sale_line_id.qty_delivered = False, False


class ProjectTaskInvoiceSaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        res = super(ProjectTaskInvoiceSaleOrder, self).action_invoice_create(grouped=False, final=False)

        # Valorisation de la date de facturation des tâches liées au lignes facturées
        invoices = self.env['account.invoice'].search([('id', '=', res[0])])
        date_invoice = invoices[0].date
        if not date_invoice:
            date_invoice = fields.Date.today()
        sale_order_lines = self.env['sale.order.line'].search([('order_id', '=', self.id)])
        tasks = self.env['project.task'].search([('initial_sale_line_id', 'in', sale_order_lines.ids)])
        tasks.write({'date_invoiced': date_invoice})

        return res


class ProjectTaskInvoiceSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_self_qty_equal_task_qty = fields.Boolean(u"Check Qty", compute='_compute_is_self_qty_equal_task_qty')

    @api.multi
    def _compute_is_self_qty_equal_task_qty(self):
        tasks = self.env['project.task'].search([('initial_sale_line_id', '=', self.id)])
        for rec in self:
            rec.is_self_qty_equal_task_qty = all(task.time_spent == rec.product_uom_qty for task in tasks)

