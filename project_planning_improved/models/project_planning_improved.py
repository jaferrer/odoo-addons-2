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

import logging

from dateutil.relativedelta import relativedelta
from openerp import models, fields, api, _
from openerp.exceptions import UserError
from openerp.report import report_sxw

_logger = logging.getLogger(__name__)


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
            domain_tasks = [('project_id', '=', rec.id),
                            ('previous_task_ids', '=', False),
                            ('children_task_ids', '=', False)]
            latest_tasks = self.env['project.task'].search(domain_tasks)
            longest_ways_to_tasks = {task: {'tasks': task, 'nb_days': task.objective_duration} for task in latest_tasks}
            while latest_tasks:
                new_tasks_to_proceed = self.env['project.task']
                for latest_task in latest_tasks:
                    new_tasks_to_proceed |= self.env['project.task']. \
                        search([('id', 'child_of', latest_task.next_task_ids.ids),
                                ('children_task_ids', '=', False)])
                    for next_task in latest_task.next_task_ids:
                        set_new_way = True
                        if next_task in longest_ways_to_tasks.keys():
                            old_duration_to_task = longest_ways_to_tasks[next_task]['nb_days']
                            new_duration_to_task = longest_ways_to_tasks[latest_task]['nb_days'] + \
                                next_task.objective_duration
                            if new_duration_to_task <= old_duration_to_task:
                                set_new_way = False
                                # Case of two critical ways
                                if new_duration_to_task == old_duration_to_task:
                                    longest_ways_to_tasks[next_task]['tasks'] |= \
                                        longest_ways_to_tasks[latest_task]['tasks']
                        if set_new_way:
                            longest_ways_to_tasks[next_task] = {
                                'tasks': longest_ways_to_tasks[latest_task]['tasks'] + next_task,
                                'nb_days': longest_ways_to_tasks[latest_task]['nb_days'] + next_task.objective_duration
                            }
                latest_tasks = new_tasks_to_proceed
            critical_nb_days = longest_ways_to_tasks and \
                               max([longest_ways_to_tasks[task]['nb_days'] for task in
                                    longest_ways_to_tasks.keys()]) or 0
            critical_tasks = self.env['project.task']
            for task in longest_ways_to_tasks.keys():
                if longest_ways_to_tasks[task]['nb_days'] == critical_nb_days:
                    critical_tasks |= longest_ways_to_tasks[task]['tasks']
            not_critical_tasks = self.env['project.task'].search([('project_id', '=', rec.id),
                                                                  ('id', 'not in', critical_tasks.ids)])
            critical_tasks.write({'critical_task': True})
            not_critical_tasks.write({'critical_task': False})

    @api.multi
    def open_tasks_timeline(self):
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
    def get_reference_task(self):
        self.ensure_one()
        return self.reference_task_id

    @api.multi
    def start_auto_planning(self):
        for rec in self:
            rec.update_critical_tasks()
            reference_task = rec.get_reference_task()
            if reference_task and rec.reference_task_end_date:
                rec.reset_dates()
                rec.update_objective_dates(reference_task)
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
        return self.open_tasks_timeline()

    @api.multi
    def reset_dates(self):
        values = {'objective_start_date': False, 'objective_end_date': False}
        tasks = self.env['project.task'].search([('project_id', 'in', self.ids),
                                                 '|', ('objective_start_date', '!=', False),
                                                 ('objective_end_date', '!=', False)])
        tasks.with_context(do_not_propagate_dates=True).write(values)

    @api.multi
    def update_objective_dates(self, reference_task=False):
        for rec in self:
            reference_task = reference_task or rec.reference_task_id
            if not reference_task or not rec.reference_task_end_date:
                raise UserError(_(u"Impossible to update objective dates for project %s if reference task or its date "
                                  u"is not defined.") % rec.display_name)
            end_date_dt = fields.Datetime.from_string(rec.reference_task_end_date)
            end_date_reference_task = fields.Datetime.to_string(reference_task.get_end_day_date(end_date_dt))
            reference_task.objective_end_date = end_date_reference_task
            previous_tasks = reference_task.previous_task_ids
            next_tasks = reference_task.next_task_ids
            planned_tasks = reference_task
            while previous_tasks or next_tasks:
                new_previous_tasks = self.env['project.task']
                new_next_tasks = self.env['project.task']
                for previous_task in previous_tasks:
                    next_tasks_start_dates = [task.objective_start_date for task in previous_task.next_task_ids if
                                              task.objective_start_date]
                    objective_end_date = min(next_tasks_start_dates or [False])
                    if objective_end_date:
                        objective_end_date_dt = fields.Datetime.from_string(objective_end_date)
                        objective_end_date = fields.Datetime. \
                            to_string(previous_task.get_effective_end_date(objective_end_date_dt))
                    previous_task.objective_end_date = objective_end_date
                    planned_tasks |= previous_task
                    new_previous_tasks |= previous_task.previous_task_ids. \
                        filtered(lambda task: task not in planned_tasks and
                                 not (task.critical_task and not previous_task.critical_task))
                    new_next_tasks |= previous_task.next_task_ids. \
                        filtered(lambda task: task not in planned_tasks and
                                 not (task.critical_task and not previous_task.critical_task))
                for next_task in next_tasks:
                    previous_tasks_end_dates = [task.objective_end_date for task in next_task.previous_task_ids if
                                                task.objective_end_date]
                    objective_start_date = max(previous_tasks_end_dates or [False])
                    if objective_start_date:
                        objective_start_date_dt = fields.Datetime.from_string(objective_start_date)
                        objective_start_date = fields.Datetime. \
                            to_string(next_task.get_effective_start_date(objective_start_date_dt))
                    next_task.set_objective_end_date_from_start_date(objective_start_date)
                    planned_tasks |= next_task
                    new_previous_tasks |= next_task.previous_task_ids. \
                        filtered(lambda task: task not in planned_tasks and
                                 not (task.critical_task and not next_task.critical_task))
                    new_next_tasks |= next_task.next_task_ids. \
                        filtered(lambda task: task not in planned_tasks and
                                 not (task.critical_task and not next_task.critical_task))
                previous_tasks = new_previous_tasks.filtered(lambda task: task not in planned_tasks)
                next_tasks = new_next_tasks.filtered(lambda task: task not in planned_tasks)

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
            parent_tasks = self.env['project.task']
            domain_not_planned_tasks = [('project_id', '=', rec.id),
                                        ('children_task_ids', '=', False),
                                        '|', ('expected_start_date', '=', False),
                                        ('expected_end_date', '=', False)]
            not_planned_tasks_with_ancestors = self.env['project.task']. \
                search(domain_not_planned_tasks + [('previous_task_ids', '!=', False)])
            for task in not_planned_tasks_with_ancestors:
                start_date = max([pt.expected_end_date for pt in task.previous_task_ids])
                parent_tasks |= task.get_all_parent_tasks()
                if start_date:
                    task.reschedule_start_date(start_date)
            not_planned_tasks_with_successors = self.env['project.task']. \
                search(domain_not_planned_tasks + [('next_task_ids', '!=', False)])
            for task in not_planned_tasks_with_successors:
                end_date = min([pt.expected_start_date for pt in task.next_task_ids])
                parent_tasks |= task.get_all_parent_tasks()
                if end_date:
                    task.reschedule_end_date(end_date)
            still_not_planned_tasks = self.env['project.task'].search(domain_not_planned_tasks)
            for task in still_not_planned_tasks:
                parent_tasks |= task.get_all_parent_tasks()
                task.with_context(do_not_propagate_dates=True, force_update_tia=True).write({
                    'expected_start_date': task.objective_start_date,
                    'expected_end_date': task.objective_end_date,
                })
            for parent_task in parent_tasks:
                children_tasks = self.env['project.task'].search([('id', 'child_of', parent_task.id),
                                                                  ('children_task_ids', '=', False),
                                                                  ('id', '!=', parent_task.id)])
                start_date = min([task.expected_start_date for task in children_tasks])
                end_date = max([task.expected_end_date for task in children_tasks])
                if end_date and parent_task.expected_end_date != end_date:
                    parent_task.with_context(do_not_propagate_dates=True).write({
                        'expected_start_date': start_date,
                        'expected_end_date': end_date,
                    })
            rec.reference_task_id.taken_into_account = True

    @api.multi
    def set_tasks_not_tia(self, new_vals):
        vals = new_vals or {}
        vals['taken_into_account'] = False
        tasks = self.env['project.task'].search([('project_id', 'in', self.ids)])
        tasks.write(vals)
        return tasks

    @api.multi
    def reset_scheduling(self):
        self.with_context(force_objective_start_date=False).set_tasks_not_tia(new_vals={'objective_end_date': False,
                                                                                        'expected_start_date': False,
                                                                                        'expected_end_date': False})


class ProjectImprovedTask(models.Model):
    _inherit = 'project.task'
    _parent_name = 'parent_task_id'

    parent_task_id = fields.Many2one('project.task', string=u"Parent task", index=True)
    previous_task_ids = fields.Many2many('project.task', 'project_task_order_rel', 'next_task_id',
                                         'previous_task_id', string=u"Previous tasks")
    next_task_ids = fields.Many2many('project.task', 'project_task_order_rel', 'previous_task_id',
                                     'next_task_id', string=u"Next tasks")
    critical_task = fields.Boolean(string=u"Critical task", readonly=True)
    objective_duration = fields.Integer(string=u"Objective Needed Time (in days)")
    children_task_ids = fields.One2many('project.task', 'parent_task_id', string=u"Children tasks")
    objective_end_date = fields.Datetime(string=u"Objective end date", readonly=True)
    objective_start_date = fields.Datetime(string=u"Objective start date", compute='_compute_objective_start_date',
                                           store=True)
    expected_start_date = fields.Datetime(string=u"Expected start date")
    expected_end_date = fields.Datetime(string=u"Expected end date")
    expected_duration = fields.Float(string=u"Expected duration (days)", compute='_compute_expected_duration',
                                     store=True)
    allocated_duration = fields.Float(string=u"Allocated duration", help=u"In project time unit of the company")
    allocated_duration_unit_tasks = fields.Float(string=u"Allocated duration for unit tasks",
                                                 help=u"In project time unit of the comany",
                                                 compute='_get_allocated_duration')
    total_allocated_duration = fields.Integer(string=u"Total allocated duration", compute='_get_allocated_duration',
                                              help=u"In project time unit of the comany")
    taken_into_account = fields.Boolean(string=u"Taken into account")
    conflict = fields.Boolean(string=u"Conflict")
    is_milestone = fields.Boolean(string="Is milestone", compute="_get_is_milestone", store=True, default=False)
    ready_for_execution = fields.Boolean(string=u"Ready for execution", readonly=True, track_visibility=True)
    notify_users_when_dates_change = fields.Boolean(string=u"Notify users when dates change",
                                                    help=u"An additional list of users is defined in project "
                                                         u"configuration")

    @api.constrains('expected_start_date', 'expected_end_date')
    def constraint_dates_consistency(self):
        self.check_dates_working_days()

    @api.multi
    @api.depends('expected_start_date', 'expected_end_date')
    def _compute_expected_duration(self):
        for rec in self:
            _, calendar = rec.get_default_calendar_and_resource()
            attendances = calendar.attendance_ids
            nb_working_hours_by_week = sum([abs(attendance.hour_to - attendance.hour_from) for
                                            attendance in attendances])
            nb_working_days = len(list(set([attendance.dayofweek for attendance in attendances]))) or 5
            nb_working_hours_by_day = float(nb_working_hours_by_week) / nb_working_days
            rec.expected_duration = rec.expected_start_date and rec.expected_end_date and \
                float(rec.get_nb_working_hours_from_expected_dates()[1]) / nb_working_hours_by_day or 0

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

    @api.depends('expected_start_date', 'expected_end_date')
    def _get_is_milestone(self):
        for rec in self:
            rec.is_milestone = rec.expected_start_date == rec.expected_end_date

    @api.onchange('expected_start_date', 'expected_end_date')
    @api.multi
    def onchange_expected_dates(self):
        for rec in self:
            rec.taken_into_account = True

    @api.multi
    def get_default_calendar_and_resource(self):
        use_calendar = not self.env.context.get('do_not_use_any_calendar')
        resource = False
        reference_user = self.user_id or self.env.user
        if reference_user:
            resource = self.env['resource.resource'].search(
                [('user_id', '=', reference_user.id), ('resource_type', '=', 'user')], limit=1)
        if not resource:
            resource = self.env['resource.resource'].search([('user_id', '=', self.env.user.id),
                                                             ('resource_type', '=', 'user')], limit=1)
        calendar = False
        if use_calendar:
            calendar = resource and resource.calendar_id or self.company_id.calendar_id or \
                self.env.ref('resource_improved.default_calendar')
        return resource, calendar

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
        resource, calendar = self.get_default_calendar_and_resource()
        target_date = date_ref
        if nb_days:
            if calendar:
                if nb_days > 0:
                    nb_days += 1
                target_date = calendar.schedule_days_get_date(nb_days, target_date, compute_leaves=True,
                                                              resource_id=resource and resource.id or False)
                target_date = target_date and target_date[0] or False
            else:
                target_date = target_date + relativedelta(days=nb_days)
        if nb_hours:
            if calendar:
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
                target_date = target_date + relativedelta(hours=nb_hours)
        return target_date

    @api.multi
    def get_nb_working_hours_from_expected_dates(self):
        self.ensure_one()
        resource, calendar = self.get_default_calendar_and_resource()
        nb_days = 0
        nb_hours = 0
        if self.expected_start_date and self.expected_end_date:
            if self.expected_start_date[:10] == self.expected_end_date[:10]:
                nb_hours = calendar.get_working_hours_of_date(fields.Datetime.from_string(self.expected_start_date),
                                                              fields.Datetime.from_string(self.expected_end_date),
                                                              compute_leaves=True, resource_id=resource.id)
            else:
                nb_hours = calendar.get_working_hours(fields.Datetime.from_string(self.expected_start_date),
                                                      fields.Datetime.from_string(self.expected_end_date),
                                                      compute_leaves=True, resource_id=resource.id)
            nb_hours = nb_hours and nb_hours[0] or 0
        else:
            nb_days = self.objective_duration
        return nb_days, nb_hours

    @api.depends('objective_end_date', 'objective_duration')
    @api.multi
    def _compute_objective_start_date(self):
        for rec in self:
            # We do not use 'get' on context, because value of key force_objective_start_date can be False.
            if 'force_objective_start_date' in self.env.context:
                rec.objective_start_date = self.env.context['force_objective_start_date']
                continue
            duration = rec.objective_duration
            if duration == 0:
                rec.objective_start_date = rec.objective_end_date
                continue
            objective_start_date = rec.objective_end_date and \
                rec.get_start_day_date(fields.Datetime.from_string(rec.objective_end_date)) or False
            # objective_start_date is at the beginning of a day and and objective_end_date as at the end of a day,
            # so if the required duration is 1 day, whe have got nothing to to.
            if duration != 1:
                objective_start_date = objective_start_date and \
                    rec.schedule_get_date(objective_start_date, nb_days=-duration+1) or False
                # We compute date from the beginning of the day, to force the start day calculation
                objective_start_date = objective_start_date and \
                    rec.get_effective_start_date(objective_start_date.replace(hour=0, minute=0, second=0)) or False
            rec.objective_start_date = objective_start_date or False
            assert rec.is_date_end_after_date_start(rec.objective_end_date, rec.objective_start_date), \
                u"Error in objective start date calculation"

    @api.multi
    def set_objective_end_date_from_start_date(self, objective_start_date):
        force_objective_end_date = self.env.context.get('force_objective_end_date')
        for rec in self:
            # We have to schedule from yesterday (if not, date + 1day can be equal to date)
            objective_end_date = fields.Datetime.from_string(objective_start_date)
            nb_days = rec.objective_duration >= 1 and rec.objective_duration - 1 or 0
            if nb_days:
                objective_end_date = objective_end_date and \
                    rec.schedule_get_date(objective_end_date, nb_days=nb_days) or False
            objective_end_date = objective_end_date and rec.get_end_day_date(objective_end_date) or False
            objective_end_date = objective_end_date and fields.Datetime.to_string(objective_end_date) or False
            rec.write({'objective_end_date': force_objective_end_date or objective_end_date or False})
            assert rec.is_date_end_after_date_start(rec.objective_end_date, rec.objective_start_date), \
                u"Error in objective end date calculation"

    @api.multi
    def get_all_parent_tasks(self, only_not_tia=False):
        self.ensure_one()
        parent_tasks = self.parent_task_id
        parent = self.parent_task_id
        while parent.parent_task_id:
            parent = parent.parent_task_id
            parent_tasks |= parent.parent_task_id
        if only_not_tia:
            return self.env['project.task'].search([('id', 'in', parent_tasks.ids),
                                                    ('taken_into_account', '=', False)])
        return parent_tasks

    @api.model
    def is_date_end_after_date_start(self, date_end, date_start):
        return date_end >= date_start

    @api.multi
    def check_expected_dates_consistency(self, expected_start_date=None, expected_end_date=None):
        for rec in self:
            expected_start_date = expected_start_date or rec.expected_start_date
            expected_end_date = expected_end_date or rec.expected_end_date
            if expected_start_date != expected_end_date and \
                    rec.is_date_end_after_date_start(expected_start_date, expected_end_date):
                raise UserError(_(u"Task %s: expected end date can not be before expected start date") %
                                rec.name)

    @api.multi
    def check_dates_working_days(self, expected_start_date=None, expected_end_date=None):
        for rec in self:
            expected_start_date = expected_start_date or rec.expected_start_date
            expected_end_date = expected_end_date or rec.expected_end_date
            if expected_start_date and not rec.is_working_day(fields.Datetime.from_string(expected_start_date)):
                raise UserError(_(u"Task %s: impossible to set start date in a not working period (%s)") %
                                (rec.display_name, expected_start_date[:10]))
            if expected_end_date and not rec.is_working_day(fields.Datetime.from_string(expected_end_date)):
                raise UserError(_(u"Task %s: impossible to set end date in a not working period (%s)") %
                                (rec.display_name, expected_end_date[:10]))

    @api.model
    def is_time_interval_included_in_another(self, start_date_1, end_date_1, start_date_2, end_date_2):
        """This function checks if interval [start_date_1, end_date_1] is included in
        interval [start_date_2, end_date_2]"""
        expected_start_date_ok = True
        expected_end_date_ok = True
        if start_date_1 and start_date_2:
            expected_start_date_ok = self.is_date_end_after_date_start(start_date_1, start_date_2)
        if expected_start_date_ok and end_date_1 and end_date_2:
            expected_end_date_ok = self.is_date_end_after_date_start(end_date_2, end_date_1)
        if expected_start_date_ok and expected_end_date_ok:
            return True
        return False

    @api.multi
    def check_dates_consistency_with_parents(self, expected_start_date=None, expected_end_date=None):
        for rec in self:
            expected_start_date = expected_start_date or rec.expected_start_date
            expected_end_date = expected_end_date or rec.expected_end_date
            parent_tasks = rec.get_all_parent_tasks()
            for parent_task in parent_tasks:
                if not self.is_time_interval_included_in_another(expected_start_date, expected_end_date,
                                                                 parent_task.expected_start_date,
                                                                 parent_task.expected_end_date):
                    raise UserError(_(u"Task %s must be totally included in parent task %s") %
                                    (rec.name, parent_task.name))

    @api.multi
    def check_dates_consistency_with_children(self, expected_start_date=None, expected_end_date=None, only_tia=True):
        for rec in self:
            if rec.project_id:
                expected_start_date = expected_start_date or rec.expected_start_date
                expected_end_date = expected_end_date or rec.expected_end_date
                domain = [('project_id', '=', rec.project_id.id),
                          ('id', 'child_of', rec.id),
                          ('id', '!=', rec.id)]
                if only_tia:
                    domain += [('taken_into_account', '=', True)]
                children_tasks_to_check = self.env['project.task'].search(domain)
                for child_task_to_check in children_tasks_to_check:
                    if not self.is_time_interval_included_in_another(child_task_to_check.expected_start_date,
                                                                     child_task_to_check.expected_end_date,
                                                                     expected_start_date, expected_end_date):
                        raise UserError(_(u"Task %s must totally include task %s") %
                                        (rec.name, child_task_to_check.name))

    @api.multi
    def get_dict_to_reschedule_start_date(self, new_date):
        self.ensure_one()
        new_expected_start_date = new_date
        nb_days, nb_hours = self.get_nb_working_hours_from_expected_dates() or (0, 0)
        if nb_hours:
            new_expected_end_date = fields.Datetime.to_string(
                self.schedule_get_date(fields.Datetime.from_string(new_date), nb_hours=nb_hours))
        elif nb_days:
            new_expected_end_date = fields.Datetime.to_string(
                self.schedule_get_date(fields.Datetime.from_string(new_date), nb_days=nb_days))
        else:
            new_expected_end_date = new_expected_start_date
        result = {}
        if self.expected_start_date != new_expected_start_date:
            result['expected_start_date'] = new_expected_start_date
        if self.expected_end_date != new_expected_end_date:
            result['expected_end_date'] = new_expected_end_date
        return result

    @api.multi
    def reschedule_start_date(self, new_date):
        for rec in self:
            dict_to_reschedule_start_date = rec.get_dict_to_reschedule_start_date(new_date)
            if dict_to_reschedule_start_date:
                rec.write(dict_to_reschedule_start_date)

    @api.multi
    def get_dict_to_reschedule_end_date(self, new_date):
        self.ensure_one()
        new_expected_end_date = new_date
        nb_days, nb_hours = self.get_nb_working_hours_from_expected_dates() or 0
        new_expected_start_date = fields.Datetime. \
            to_string(self.schedule_get_date(fields.Datetime.from_string(new_date), nb_hours=-nb_hours))
        result = {}
        if self.expected_start_date != new_expected_start_date:
            result['expected_start_date'] = new_expected_start_date
        if self.expected_end_date != new_expected_end_date:
            result['expected_end_date'] = new_expected_end_date
        return result

    @api.multi
    def reschedule_end_date(self, new_date):
        for rec in self:
            dict_to_reschedule_end_date = rec.get_dict_to_reschedule_end_date(new_date)
            if dict_to_reschedule_end_date:
                rec.write(dict_to_reschedule_end_date)

    @api.multi
    def check_dates(self):
        self.check_expected_dates_consistency()
        self.check_dates_consistency_with_parents()
        self.check_dates_consistency_with_children()

    @api.multi
    def propagate_dates(self):
        self.ensure_one()
        next_tasks_to_reschedule = self.env['project.task']
        for task in self.next_task_ids:
            if self.expected_end_date > task.expected_start_date:
                next_tasks_to_reschedule |= task
        next_tasks_to_reschedule.reschedule_start_date(self.expected_end_date)
        previous_tasks_to_reschedule = self.env['project.task']
        for task in self.previous_task_ids:
            if self.expected_start_date < task.expected_end_date:
                previous_tasks_to_reschedule |= task
        previous_tasks_to_reschedule.reschedule_end_date(self.expected_start_date)
        self.env['project.task'].search([
            ('id', 'child_of', self.children_task_ids.ids),
            ('expected_end_date', '>', self.expected_end_date),
            '|', ('next_task_ids', '=', False),
            ('next_task_ids.parent_task_id', '!=', self.id),
        ], order='expected_end_date desc').reschedule_end_date(self.expected_end_date)
        self.env['project.task'].search([
            ('id', 'child_of', self.children_task_ids.ids),
            ('expected_start_date', '<', self.expected_start_date),
            '|', ('previous_task_ids', '=', False),
            ('previous_task_ids.parent_task_id', '!=', self.id),
        ], order='expected_start_date asc').reschedule_start_date(self.expected_start_date)
        self.reschedule_parent_dates()

    @api.multi
    def reschedule_parent_dates(self):
        self.ensure_one()
        if self.parent_task_id.expected_end_date and \
                self.parent_task_id.expected_end_date < self.expected_end_date:
            vals = {'expected_end_date': self.expected_end_date}
            if self.expected_end_date < self.parent_task_id.expected_start_date:
                vals['expected_start_date'] = self.expected_end_date
            self.parent_task_id.write(vals)
        if self.parent_task_id.expected_start_date and \
                self.parent_task_id.expected_start_date > self.expected_start_date:
            self.parent_task_id.expected_start_date = self.expected_start_date
            vals = {'expected_start_date': self.expected_start_date}
            if self.expected_start_date > self.parent_task_id.expected_end_date:
                vals['expected_end_date'] = self.expected_start_date
            self.parent_task_id.write(vals)

    @api.multi
    def get_start_day_date(self, date=None):
        self.ensure_one()
        if not date:
            date = fields.Datetime.from_string(self.expected_start_date)
        resource, calendar = self.get_default_calendar_and_resource()
        if calendar:
            return calendar.get_start_day_date(date, compute_leaves=True, resource_id=resource and resource.id or False)
        return date.replace(hour=0, minute=0, second=0)

    @api.multi
    def get_end_day_date(self, date=None):
        self.ensure_one()
        if not date:
            date = fields.Datetime.from_string(self.expected_end_date)
        resource, calendar = self.get_default_calendar_and_resource()
        if calendar:
            return calendar.get_end_day_date(date, compute_leaves=True, resource_id=resource and resource.id or False)
        return date.replace(hour=23, minute=59, second=59)

    @api.multi
    def get_effective_start_date(self, date):
        self.ensure_one()
        resource, calendar = self.get_default_calendar_and_resource()
        date_next_working_day = date
        if date and calendar:
            if not self.is_working_day(date):
                return date
            nb_iterations = 0
            while nb_iterations < 100:
                nb_iterations += 1
                list_intervals = calendar.get_working_intervals_of_day(start_dt=date_next_working_day,
                                                                       compute_leaves=True,
                                                                       resource_id=resource and resource.id or False)
                if list_intervals and list_intervals[0] and list_intervals[0][0]:
                    date_next_working_day = list_intervals[0][0][0]
                    date_next_working_day = self.get_start_day_date(date_next_working_day)
                    break
                else:
                    date_next_working_day = date_next_working_day.replace(hour=0, minute=0, second=0) + \
                        relativedelta(days=1)
        return date_next_working_day

    @api.multi
    def get_effective_end_date(self, date):
        self.ensure_one()
        resource, calendar = self.get_default_calendar_and_resource()
        date_previous_working_day = date
        if date and calendar:
            if not self.is_working_day(date):
                return date
            nb_iterations = 0
            while nb_iterations < 100:
                list_intervals = calendar.get_working_intervals_of_day(end_dt=date_previous_working_day,
                                                                       compute_leaves=True,
                                                                       resource_id=resource and resource.id or False)
                if list_intervals and list_intervals[-1] and list_intervals[-1][-1]:
                    date_previous_working_day = list_intervals[-1][-1][-1]
                    date_previous_working_day = self.get_end_day_date(date_previous_working_day)
                    break
                else:
                    date_previous_working_day = date_previous_working_day.replace(hour=23, minute=59, second=59) - \
                        relativedelta(days=1)
        return date_previous_working_day

    @api.multi
    def get_dates_start_end_day(self, vals):
        if self and vals.get('expected_start_date') and vals.get('expected_end_date'):
            if vals['expected_start_date'] == vals['expected_end_date']:
                return vals
            start_dt = fields.Datetime.from_string(vals['expected_start_date'])
            end_dt = fields.Datetime.from_string(vals['expected_end_date'])
            is_start_date_in_working_day = self[0].is_working_day(start_dt)
            is_end_date_in_working_day = self[0].is_working_day(end_dt)
            if is_start_date_in_working_day and is_end_date_in_working_day:
                day_intervals_after_start = self[0].get_working_intervals(date_start=start_dt)
                day_intervals_after_start = day_intervals_after_start and day_intervals_after_start[0] or False
                day_intervals_before_end = self[0].get_working_intervals(date_end=end_dt)
                day_intervals_before_end = day_intervals_before_end and day_intervals_before_end[0] or False
                if not day_intervals_after_start and not day_intervals_before_end:
                    # Case when scheduling a task from 23h to 1h the day after, for instance
                    new_expected_start_date_dt = self[0].get_start_day_date(start_dt)
                    vals['expected_start_date'] = fields.Datetime.to_string(new_expected_start_date_dt)
                    new_expected_end_date_dt = self[0].get_end_day_date(end_dt)
                    vals['expected_end_date'] = fields.Datetime.to_string(new_expected_end_date_dt)
                    return vals
        if self and vals.get('expected_start_date'):
            if len(vals['expected_start_date']) == 10:
                vals['expected_start_date'] += ' 12:00:00'
            expected_start_date_dt = fields.Datetime.from_string(vals['expected_start_date'])
            checked_expected_start_date_dt = self[0].get_effective_start_date(expected_start_date_dt)
            new_expected_start_date_dt = self[0].get_start_day_date(checked_expected_start_date_dt)
            vals['expected_start_date'] = fields.Datetime.to_string(new_expected_start_date_dt)
        if self and vals.get('expected_end_date'):
            if len(vals['expected_end_date']) == 10:
                vals['expected_end_date'] += ' 12:00:00'
            expected_end_date_dt = fields.Datetime.from_string(vals['expected_end_date'])
            checked_end_date_dt = self[0].get_effective_end_date(expected_end_date_dt)
            new_expected_end_date_dt = self[0].get_end_day_date(checked_end_date_dt)
            vals['expected_end_date'] = fields.Datetime.to_string(new_expected_end_date_dt)
        return vals

    @api.multi
    def check_not_tia(self):
        for rec in self:
            if rec.taken_into_account:
                raise UserError(_(u"Impossible to schedule task %s, because it is already taken into account") %
                                rec.display_name)

    @api.multi
    def is_automanaged_view(self):
        # TODO: timeline est passé même en vue formulaire
        return self.env.context.get('params', {}).get('view_type') == 'timeline'

    @api.multi
    def write(self, vals):
        if 'objective_end_date' in vals:
            _logger.info(u"Scheduling task(s) %s for objective end date %s", u",".join([rec.name for rec in self]),
                         vals.get('objective_end_date'))
        dates_changed = (vals.get('expected_start_date') or vals.get('expected_end_date')) and True or False
        propagate_dates = not self.env.context.get('do_not_propagate_dates')
        propagating_tasks = self.env.context.get('propagating_tasks')
        slide_tasks = self.get_slide_tasks(vals)
        vals = self.get_dates_start_end_day(vals)
        for rec in self:
            if dates_changed and 'taken_into_account' not in vals and not self.env.context.get('force_update_tia'):
                self.check_not_tia()
            vals_copy = vals.copy()
            if slide_tasks[rec] and not propagating_tasks:
                new_end_date_dict = rec.get_dict_to_reschedule_start_date(vals_copy['expected_start_date'])
                new_end_date = new_end_date_dict.get('expected_end_date', vals_copy['expected_end_date'])
                new_end_date = rec.get_end_day_date(fields.Datetime.from_string(new_end_date))
                new_end_date = fields.Datetime.to_string(new_end_date)
                vals_copy['expected_end_date'] = new_end_date
            super(ProjectImprovedTask, rec).write(vals_copy)
            if rec.expected_start_date and rec.expected_end_date and propagate_dates and dates_changed:
                rec.with_context(propagating_tasks=True).propagate_dates()
                # Unit tests should cover the potential cases of ond "check_dates" function
                # rec.check_dates()
        self.notify_users_if_needed(vals)
        return True

    @api.multi
    def notify_users_if_needed(self, vals):
        dates_changed = (vals.get('expected_start_date') or vals.get('expected_end_date')) and True or False
        for rec in self:
            if dates_changed and rec.notify_users_when_dates_change:
                rec.notify_users_for_date_change()

    @api.multi
    def get_partner_to_notify_ids(self):
        self.ensure_one()
        partners_to_notify_config = self.env['ir.config_parameter']. \
            get_param('project_planning_improved.notify_date_changes_for_partner_ids', '[]')
        return eval(partners_to_notify_config) or []

    @api.multi
    def get_notification_subject(self):
        self.ensure_one()
        return _(u"Replanification of task %s in project %s") % (self.display_name, self.project_id.display_name)

    @api.multi
    def get_notification_body(self):
        self.ensure_one()
        rml_obj = report_sxw.rml_parse(self.env.cr, self.env.uid, 'project.task', dict(self.env.context))
        rml_obj.localcontext.update({'lang': self.env.context.get('lang', False)})
        return _(u"%s has changed the dates of task %s in project %s: expected start date %s, expected end date %s.") % \
            (self.env.user.partner_id.name, self.display_name, self.project_id.display_name,
             rml_obj.formatLang(self.expected_start_date[:10], date=True),
             rml_obj.formatLang(self.expected_end_date[:10], date=True))

    @api.multi
    def notify_users_for_date_change(self):
        self.ensure_one()
        email_from = self.env['mail.message']._get_default_from()
        partner_to_notify_ids = self.get_partner_to_notify_ids()
        for rec in self:
            for partner_id in partner_to_notify_ids:
                if partner_id == self.env.user.partner_id.id:
                    continue
                partner = self.env['res.partner'].browse(partner_id)
                channels = self.env['mail.channel']. \
                    search([('channel_partner_ids', '=', partner_id),
                            ('channel_partner_ids', '=', self.env.user.partner_id.id),
                            ('email_send', '=', False),
                            ('group_ids', '=', False)])
                chosen_channel = self.env['mail.channel']
                for channel in channels:
                    if len(channel.channel_partner_ids) == 2:
                        chosen_channel = channel
                        break
                if not chosen_channel:
                    chosen_channel = self.env['mail.channel'].create({
                        'name': "%s, %s" % (partner.name, self.env.user.partner_id.name),
                        'public': 'private',
                        'email_send': False,
                        'channel_partner_ids': [(6, 0, [partner_id, self.env.user.partner_id.id])]
                    })
                message = self.env['mail.message'].create({
                    'subject': rec.get_notification_subject(),
                    'body': rec.get_notification_body(),
                    'record_name': rec.name,
                    'email_from': email_from,
                    'reply_to': email_from,
                    'model': 'project.task',
                    'res_id': rec.id,
                    'no_auto_thread': True,
                    'channel_ids': [(6, 0, chosen_channel.ids)],
                })
                partner.with_context(auto_delete=True)._notify(message, force_send=True, user_signature=True)

    @api.multi
    def get_slide_tasks(self, vals):
        slide_tasks = {rec: False for rec in self}
        if self.is_automanaged_view() and 'expected_start_date' in vals and 'expected_end_date' in vals:
            for rec in self:
                if not rec.expected_start_date or not rec.expected_end_date:
                    continue
                old_start_date_dt = fields.Datetime.from_string(rec.expected_start_date)
                old_end_date_dt = fields.Datetime.from_string(rec.expected_end_date)
                new_start_date_dt = fields.Datetime.from_string(vals['expected_start_date'])
                new_end_date_dt = fields.Datetime.from_string(vals['expected_end_date'])
                slide_tasks[rec] = old_end_date_dt - old_start_date_dt == new_end_date_dt - new_start_date_dt
        return slide_tasks

    @api.multi
    def is_working_day(self, date):
        self.ensure_one()
        resource, calendar = self[0].get_default_calendar_and_resource()
        list_intervals = False
        if calendar:
            list_intervals = calendar.get_working_intervals_of_day(start_dt=date.replace(hour=0, minute=0, second=0),
                                                                   compute_leaves=True,
                                                                   resource_id=resource and resource.id or False)
        return list_intervals and list_intervals[0] and True or False

    @api.multi
    def get_working_intervals(self, date_start=None, date_end=None):
        self.ensure_one()
        resource, calendar = self[0].get_default_calendar_and_resource()
        list_intervals = False
        if calendar:
            list_intervals = calendar.get_working_intervals_of_day(start_dt=date_start, end_dt=date_end,
                                                                   compute_leaves=True,
                                                                   resource_id=resource and resource.id or False)
        return list_intervals

    @api.multi
    def get_task_number_open_days(self):
        self.ensure_one()
        open_days = 0
        start = fields.Datetime.from_string(self.expected_start_date)
        end = fields.Datetime.from_string(self.expected_end_date)
        while start <= end:
            if self.is_working_day(start):
                open_days += 1
            start += relativedelta(days=1)
        return open_days

    @api.multi
    def get_occupation_task_rate(self):
        self.ensure_one()
        task_rate = 0
        open_days = self.get_task_number_open_days()
        if open_days > 0:
            task_rate = self.allocated_duration / open_days
        return task_rate

    @api.multi
    def get_all_working_days_for_tasks(self):
        list_working_days = []
        if self:
            min_date = min([task.expected_start_date for task in self if task.expected_start_date])
            max_date = max([task.expected_end_date for task in self if task.expected_end_date])
            if min_date and max_date:
                ref_date = fields.Datetime.from_string(min_date).replace(hour=0, minute=0, second=0)
                max_date = fields.Datetime.from_string(max_date).replace(hour=0, minute=0, second=0)
                while ref_date <= max_date:
                    if self[0].is_working_day(ref_date):
                        list_working_days += [ref_date]
                    ref_date += relativedelta(days=1)
        return list_working_days

    @api.multi
    def update_ready_for_execution(self):
        for rec in self:
            rec.ready_for_execution = all([task.kanban_state == 'ready' for task in rec.previous_task_ids])

    @api.model
    def cron_update_ready_for_execution(self):
        self.search([('project_id.state', 'not in', ['cancelled', 'close'])]). \
            with_context(do_not_propagate_dates=True).update_ready_for_execution()
