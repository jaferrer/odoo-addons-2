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

from dateutil.relativedelta import relativedelta

from openerp import models, fields, api, _
from openerp.exceptions import UserError


class ProjectPlanningImprovedResUsers(models.Model):
    _inherit = 'res.users'

    @api.multi
    def get_tasks(self, start_date=None, end_date=None):
        domain = [('user_id', 'in', self.ids),
                  ('expected_start_date', '!=', False),
                  ('expected_end_date', '!=', False)]
        if start_date:
            domain += [('expected_end_date', '>', start_date)]
        if end_date:
            domain += [('expected_start_date', '<', end_date)]
        return self.env['project.task'].search(domain)


class OpenConflictTracking(models.TransientModel):
    _name = 'open.conflict.tracking'

    def _get_default_user_ids(self):
        return self.env.user

    user_ids = fields.Many2many('res.users', string=u"Users", default=_get_default_user_ids)
    start_date = fields.Datetime(string=u"Start date", default=fields.Datetime.now)
    end_date = fields.Datetime(string=u"End date")

    @api.multi
    def execute(self):
        self.ensure_one()
        conflict_tasks = self.env['project.task']
        display_tasks = self.env['project.task']
        tasks_occupation_rate = {}
        for user in self.user_ids:
            tasks_user = user.get_tasks(self.start_date, self.end_date)
            display_tasks |= tasks_user
            list_working_days = tasks_user.get_all_working_days_for_tasks()
            for working_day in list_working_days:
                date_start_day = fields.Datetime.to_string(working_day.replace(hour=0, minute=0, second=0))
                date_end_day = fields.Datetime.to_string(working_day.replace(hour=23, minute=59, second=59))
                total_task_rate = 0
                concerned_tasks = self.env['project.task'].search([('id', 'in', tasks_user.ids),
                                                                  ('expected_end_date', '>=', date_start_day),
                                                                  ('expected_start_date', '<=', date_end_day)])
                for task in concerned_tasks:
                    if task not in tasks_occupation_rate:
                        tasks_occupation_rate[task] = task.get_occupation_task_rate()
                    total_task_rate += tasks_occupation_rate[task]
                if total_task_rate > 1:
                    conflict_tasks |= concerned_tasks
        not_conflicted_tasks = self.env['project.task'].search([('id', 'in', display_tasks.ids),
                                                                ('id', 'not in', conflict_tasks.ids),
                                                                ('conflict', '=', True)])
        if not_conflicted_tasks:
            not_conflicted_tasks.write({'conflict': False})
        if display_tasks and conflict_tasks:
            conflict_tasks.write({'conflict': True})
            ctx = self.env.context.copy()
            ctx['search_default_next_month'] = True
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'project.task',
                'name': _(u"Conflicts"),
                'view_type': 'form',
                'view_mode': 'timeline,tree,form,graph',
                'domain': [('id', 'in', display_tasks.ids)],
                'context': ctx
            }
        else:
            raise UserError(_(u"No conflict found"))
