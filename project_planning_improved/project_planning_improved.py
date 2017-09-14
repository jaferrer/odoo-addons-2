# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class ProjectImprovedProject(models.Model):
    _inherit = 'project.project'

    reference_task_id = fields.Many2one('project.task', string=u"Reference task")
    reference_task_end_date = fields.Datetime(string=u"Reference task end date")

    @api.multi
    def check_modification_reference_task_allowed(self):
        current_user = self.env.user
        for rec in self:
            if rec.user_id != current_user:
                raise UserError(_(u"You are not allowed to change the reference task (or its date) for project %s, "
                                  u"because you are not manager of this project." % rec.display_name))

    @api.multi
    def write(self, vals):
        if vals.get('reference_task_id') or vals.get('reference_task_end_date'):
            self.check_modification_reference_task_allowed()
        return super(ProjectImprovedProject, self).write(vals)

    @api.multi
    def open_task_planning(self):
        self.ensure_one()
        view = self.env.ref('project_planning_improved.project_improved_task_tree')
        ctx = self.env.context.copy()
        ctx['search_default_project_id'] = self.id
        return {
            'name': _("Tasks planning for project %s") % self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'project.task',
            'views': [(view.id, 'tree')],
            'view_id': view.id,
            'context': ctx,
        }

    @api.multi
    def update_critical_tasks(self):
        for rec in self:
            domain_tasks = [('project_id', '=', rec.id), ('previous_task_ids', '=', False)]
            latest_tasks = self.env['project.task'].search(domain_tasks)
            longest_ways_to_tasks = {task: {'tasks': task, 'nb_days': task.objective_duration} for task in latest_tasks}
            while latest_tasks:
                new_tasks_to_proceed = self.env['project.task']
                for latest_task in latest_tasks:
                    new_tasks_to_proceed |= latest_task.next_task_ids
                    for next_task in latest_task.next_task_ids:
                        set_new_way = True
                        if next_task in longest_ways_to_tasks.keys():
                            old_duration_to_task = longest_ways_to_tasks[next_task]['nb_days']
                            new_duration_to_task = longest_ways_to_tasks[latest_task]['nb_days'] + next_task.objective_duration
                            if new_duration_to_task <= old_duration_to_task:
                                set_new_way = False
                                # Case of two critical ways
                                if new_duration_to_task == old_duration_to_task:
                                    longest_ways_to_tasks[next_task]['tasks'] = longest_ways_to_tasks[next_task]['tasks'] + \
                                                                                longest_ways_to_tasks[latest_task]['tasks']
                        if set_new_way:
                            longest_ways_to_tasks[next_task] = {
                                'tasks': longest_ways_to_tasks[latest_task]['tasks'] + next_task,
                                'nb_days': longest_ways_to_tasks[latest_task]['nb_days'] + next_task.objective_duration
                            }
                latest_tasks = new_tasks_to_proceed
            critical_nb_days = longest_ways_to_tasks and \
                max([longest_ways_to_tasks[task]['nb_days'] for task in longest_ways_to_tasks.keys()]) or 0
            critical_tasks = self.env['project.task']
            for task in longest_ways_to_tasks.keys():
                if longest_ways_to_tasks[task]['nb_days'] == critical_nb_days:
                    critical_tasks |= longest_ways_to_tasks[task]['tasks']
            not_critical_tasks = self.env['project.task'].search(domain_tasks + [('id', 'not in', critical_tasks.ids)])
            critical_tasks.write({'critical_task': True})
            not_critical_tasks.write({'critical_task': False})

    @api.multi
    def start_auto_planning(self):
        for rec in self:
            rec.update_critical_tasks()
            if rec.reference_task_id and rec.reference_task_end_date:
                rec.update_objective_dates()
                rec.update_objective_dates_parent_tasks()
                not_planned_tasks = self.env['project.task'].search([('project_id', '=', rec.id),
                                                                     '|', ('objective_start_date', '=', False),
                                                                     ('objective_end_date', '=', False)])
                if not_planned_tasks:
                    raise UserError(_(u"Impossible to determine objective dates for tasks %s in project %s "
                                      u"with current configuration") %
                                    (u", ".join([task.name for task in not_planned_tasks]),
                                    rec.display_name))
                rec.configure_expected_dates()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'name': _("Tasks"),
            'view_type': 'form',
            'view_mode': 'timeline,tree,form',
            'domain': [('project_id', 'in', self.ids)],
            'context': self.env.context
        }

    @api.multi
    def update_objective_dates(self):
        for rec in self:
            rec.task_ids.write({'objective_start_date': False,
                                 'objective_end_date': False})
            if not rec.reference_task_id or not rec.reference_task_end_date:
                raise UserError(_(u"Impossible to update objective dates for project %s if reference task or its date "
                                  u"is not defined.") % rec.display_name)
            rec.reference_task_id.objective_end_date = rec.reference_task_end_date
            previous_tasks = rec.reference_task_id.previous_task_ids
            next_tasks = rec.reference_task_id.next_task_ids
            planned_tasks = rec.reference_task_id
            while previous_tasks or next_tasks:
                new_previous_tasks = self.env['project.task']
                new_next_tasks = self.env['project.task']
                for previous_task in previous_tasks:
                    previous_task.objective_end_date = min([task.objective_start_date for
                                                            task in previous_task.next_task_ids if
                                                            task.objective_start_date] or [False])
                    planned_tasks |= previous_task
                    new_previous_tasks |= previous_task.previous_task_ids.filtered(lambda task: task not in planned_tasks)
                    new_next_tasks |= previous_task.next_task_ids.filtered(lambda task: task not in planned_tasks)
                for next_task in next_tasks:
                    objective_start_date = max([task.objective_end_date for
                                                task in next_task.previous_task_ids if
                                                task.objective_end_date] or [False])
                    next_task.set_objective_end_date_from_start_date(objective_start_date)
                    planned_tasks |= next_task
                    new_previous_tasks |= next_task.previous_task_ids.filtered(lambda task: task not in planned_tasks)
                    new_next_tasks |= next_task.next_task_ids.filtered(lambda task: task not in planned_tasks)
                previous_tasks = new_previous_tasks
                next_tasks = new_next_tasks

    @api.multi
    def update_objective_dates_parent_tasks(self):
        for rec in self:
            parent_tasks = self.env['project.task'].search([('project_id', '=', rec.id),
                                                            '|', ('objective_start_date', '=', False),
                                                            ('objective_end_date', '=', False)])
            for parent_task in parent_tasks:
                children_tasks = self.env['project.task'].search([('id', 'child_of', parent_task.id)])
                if children_tasks:
                    min_objective_start_date = min([task.objective_start_date for
                                                    task in children_tasks if task.objective_start_date] or [False])
                    max_objective_end_date = max([task.objective_end_date for
                                                  task in children_tasks if task.objective_end_date] or [False])
                    parent_task.with_context(force_objective_start_date=min_objective_start_date). \
                        write({'objective_end_date': max_objective_end_date})

    @api.multi
    def configure_expected_dates(self):
        for rec in self:
            tasks_not_tia = self.env['project.task'].search([('project_id', '=', rec.id),
                                                                 ('taken_into_account', '=', False)])
            for task in tasks_not_tia:
                task.with_context(do_not_update_tia=True).write({
                    'expected_start_date': task.objective_start_date,
                    'expected_end_date': task.objective_end_date,
                })


class ProjectImprovedTask(models.Model):
    _inherit = 'project.task'
    _parent_name = 'parent_task_id'

    parent_task_id = fields.Many2one('project.task', string=u"Parent task")
    previous_task_ids = fields.Many2many('project.task', 'project_task_order_rel', 'next_task_id',
                                         'previous_task_id', string=u"Previous tasks")
    next_task_ids = fields.Many2many('project.task', 'project_task_order_rel', 'previous_task_id',
                                     'next_task_id', string=u"Next tasks")
    critical_task = fields.Boolean(string=u"Critical task", readonly=True)
    objective_duration = fields.Float(string=u"Objective Needed Time",
                                      help=u"In project time unit of the comany")
    children_task_ids = fields.One2many('project.task', 'parent_task_id', string=u"Children tasks")
    objective_end_date = fields.Datetime(string=u"Objective end date", readonly=True)
    expected_end_date = fields.Datetime(string=u"Expected end date")
    objective_start_date = fields.Datetime(string=u"Objective start date", compute='_compute_objective_start_date',
                                           store=True)
    expected_start_date = fields.Datetime(string=u"Expected start date")
    allocated_duration = fields.Float(string=u"Allocated duration", help=u"In project time unit of the comany")
    allocated_duration_unit_tasks = fields.Float(string=u"Allocated duration for unit tasks",
                                             help=u"In project time unit of the comany",
                                             compute='_get_allocated_duration', store=True)
    total_allocated_duration = fields.Integer(string=u"Total allocated duration", compute='_get_allocated_duration',
                                          help=u"In project time unit of the comany", store=True)
    taken_into_account = fields.Boolean(string=u"Taken into account")
    conflict = fields.Boolean(string=u"Conflict")

    @api.depends('children_task_ids', 'children_task_ids.total_allocated_duration', 'allocated_duration')
    @api.multi
    def _get_allocated_duration(self):
        records = self
        while records:
            rec = records[0]
            if any([task in records for task in rec.children_task_ids]):
                records = records[1:]
                records += rec
            else:
                rec.allocated_duration_unit_tasks = sum(line.total_allocated_duration for
                                                        line in rec.children_task_ids)
                rec.total_allocated_duration = rec.allocated_duration + rec.allocated_duration_unit_tasks
                records -= rec

    @api.onchange('expected_start_date', 'expected_end_date')
    @api.multi
    def onchange_expected_dates(self):
        for rec in self:
            rec.taken_into_account = True

    @api.multi
    def schedule_get_date(self, date_ref, nb_days=0, nb_hours=0):
        """
        From a task (self), this function computes the date which is 'nb_days' days and 'nb_hours' hours after date
        'date_ref'.
        :param date_ref: datetime, reference date
        :param nb_days: Number of days to add/remove
        :param nb_hours: Number of hours to add/remove
        """
        self.ensure_one()
        do_not_use_any_calendar = self.env.context.get('do_not_use_any_calendar')
        resource = False
        reference_user = self.user_id or self.env.user
        if reference_user:
            resource = self.env['resource.resource'].search([('user_id', '=', reference_user.id), ('resource_type', '=', 'user')], limit=1)
        if not resource:
            resource = self.env['resource.resource'].search([('user_id', '=', self.env.user.id),
                                                             ('resource_type', '=', 'user')], limit=1)
        if resource:
            calendar = resource.calendar_id
        else:
            calendar = self.company_id.calendar_id
        if not calendar:
            calendar = self.env.ref('resource_improved.default_calendar')
        target_date = date_ref
        if nb_days:
            if calendar and not do_not_use_any_calendar:
                if nb_days > 0:
                    nb_days += 1
                target_date = calendar.schedule_days_get_date(nb_days, target_date, compute_leaves=True, resource_id=resource and resource.id or False)
                target_date = target_date and target_date[0] or False
            else:
                target_date = target_date - relativedelta(days=nb_days)
        if nb_hours:
            if calendar and not do_not_use_any_calendar:
                available_intervals = calendar.schedule_hours(nb_hours, target_date, compute_leaves=True,
                                                              resource_id=resource and resource.id or False)
                if nb_hours > 0:
                    target_date = available_intervals and \
                                  max([max([max(interval_tuple) for interval_tuple in interval_list if
                                            interval_tuple[0] != interval_tuple[1]]) for
                                       interval_list in available_intervals]) or False
                else:
                    target_date = available_intervals and \
                                  min([min([min(interval_tuple) for interval_tuple in interval_list if
                                            interval_tuple[0] != interval_tuple[1]]) for
                                       interval_list in available_intervals]) or False
            else:
                target_date = target_date - relativedelta(hours=nb_hours)
        return target_date

    @api.depends('objective_end_date', 'objective_duration')
    @api.multi
    def _compute_objective_start_date(self):
        force_objective_start_date = self.env.context.get('force_objective_start_date')
        for rec in self:
            rec.objective_start_date = force_objective_start_date or rec.objective_end_date and \
                rec.schedule_get_date(fields.Datetime.from_string(rec.objective_end_date),
                                      nb_days=-rec.objective_duration) or False

    @api.multi
    def set_objective_end_date_from_start_date(self, objective_start_date):
        force_objective_end_date = self.env.context.get('force_objective_end_date')
        for rec in self:
            rec.objective_end_date = force_objective_end_date or objective_start_date and \
                rec.schedule_get_date(fields.Datetime.from_string(objective_start_date),
                                      nb_days=rec.objective_duration) or False

    @api.multi
    def write(self, vals):
        do_not_update_tia = self.env.context.get('do_not_update_tia')
        if not do_not_update_tia and (vals.get('expected_start_date') or vals.get('expected_end_date')):
            vals['taken_into_account'] = True
        return super(ProjectImprovedTask, self).write(vals)
