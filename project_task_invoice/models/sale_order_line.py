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
from odoo.tools import float_compare


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
            rec.initial_tasks_amount = sum(rec.initial_task_ids.mapped('invoice_time'))

    @api.multi
    def _compute_is_self_qty_equal_tasks_qty(self):
        for rec in self:
            sum_time_spent = sum(rec.initial_task_ids.mapped('invoice_time'))
            compare = float_compare(rec.product_uom_qty, sum_time_spent, precision_digits=2)
            rec.wrong_task_qty = (rec.state not in ['cancel', 'done'] and rec.initial_task_ids and compare)
