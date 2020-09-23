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

from odoo import fields, models, api


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
