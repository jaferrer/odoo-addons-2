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
from odoo.tools.convert import safe_eval


class ProjectMilestone(models.Model):
    _inherit = 'project.milestone'

    nb_task_to_invoice = fields.Integer(u"# Task to invoice", compute='_compute_nb_task_to_invoice')
    invoice_tasks_total_count = fields.Integer(u"# Task invoiceable", compute='_compute_nb_task_to_invoice')

    @api.multi
    def _compute_nb_task_to_invoice(self):
        for rec in self:
            rec.nb_task_to_invoice = self.env['project.task'].search_count([
                ('milestone_id', '=', rec.id),
                ('stage_is_delivered', '=', True),
                ('date_invoiced', '=', False)
            ])
            rec.invoice_tasks_total_count = self.env['project.task'].search_count([
                ('milestone_id', '=', rec.id),
                ('stage_is_delivered', '=', True),
            ])

    @api.multi
    def see_tasks_to_invoice(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        ctx['default_project_id'] = self.project_id.id
        ctx['default_milestone_id'] = self.id
        act = self.env.ref('project_task_invoice.project_task_dashboard_invoice_action').read()[0]
        act_ctx = safe_eval(act.get('context', "{}"))
        act_ctx.pop('search_default_project', False)
        act['context'] = dict(ctx, **act_ctx)
        act['domain'] = safe_eval(act.get('domain', "[]"))
        act['domain'].append(('milestone_id', '=', self.id))
        return act
