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

from datetime import datetime as dt
import logging

from dateutil.relativedelta import relativedelta
from openerp import models, fields, api, _
from openerp.exceptions import UserError
from openerp.report import report_sxw

_logger = logging.getLogger(__name__)


class ProjectImprovedProject(models.Model):
    _inherit = 'project.project'

    reference_task_id = fields.Many2one('project.task', string=u"Reference task")
    reference_task_end_date = fields.Date(string=u"Reference task end date")

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
                rec.with_context(do_not_propagate_dates=True).configure_expected_dates()
        return self.open_tasks_timeline()

    @api.multi
    def reset_dates(self):
        tasks = self.env['project.task'].search([('project_id', 'in', self.ids),
                                                 '|', ('objective_start_date', '!=', False),
                                                 ('objective_end_date', '!=', False)])
        tasks.with_context(do_not_propagate_dates=True).write({'objective_start_date': False,
                                                               'objective_end_date': False})

    @api.multi
    def update_objective_dates(self, reference_task=False):
        for rec in self:
            reference_task = reference_task or rec.reference_task_id
            if not reference_task or not rec.reference_task_end_date:
                raise UserError(_(u"Impossible to update objective dates for project %s if reference task or its date "
                                  u"is not defined.") % rec.display_name)
            reference_task.objective_end_date = rec.reference_task_end_date
            print 'vals_ref_task', {
                'objective_start_date': reference_task.
                    schedule_get_date(rec.reference_task_end_date, -reference_task.objective_duration + 1),
                'objective_end_date': rec.reference_task_end_date,
                'objective_instant_task_start_day': False,
                'objective_instant_task_end_day': not reference_task.objective_duration,
            }
            reference_task.write({
                'objective_start_date': reference_task.
                    schedule_get_date(rec.reference_task_end_date, -reference_task.objective_duration + 1),
                'objective_end_date': rec.reference_task_end_date,
                'objective_instant_task_start_day': False,
                'objective_instant_task_end_day': not reference_task.objective_duration,
            })
            previous_tasks = reference_task.previous_task_ids
            next_tasks = reference_task.next_task_ids
            planned_tasks = reference_task
            while previous_tasks or next_tasks:
                new_previous_tasks = self.env['project.task']
                new_next_tasks = self.env['project.task']
                for previous_task in previous_tasks:
                    next_tasks_with_start_dates = self.env['project.task']. \
                        search([('id', 'in', previous_tasks.next_task_ids.ids), ('objective_start_date', '!=', False)])
                    objective_end_date = min([task.objective_start_date for task in next_tasks_with_start_dates] or
                                             [False])
                    all_next_tasks_on_end_day = \
                        next_tasks_with_start_dates and all([task.objective_instant_task_end_day for
                                                             task in next_tasks_with_start_dates]) or False
                    print 'previous', previous_task.name, objective_end_date, all_next_tasks_on_end_day
                    if objective_end_date and not all_next_tasks_on_end_day:
                        objective_end_date = previous_task.schedule_get_date(objective_end_date, -1)
                    objective_start_date = objective_end_date and previous_task. \
                        schedule_get_date(objective_end_date, -previous_task.objective_duration + 1) or False
                    vals_previous_task = {
                        'objective_start_date': objective_start_date,
                        'objective_end_date': objective_end_date,
                        'objective_instant_task_start_day': False,
                        'objective_instant_task_end_day': not previous_task.objective_duration,
                    }
                    print 'vals_previous_task', vals_previous_task
                    previous_task.write(vals_previous_task)
                    planned_tasks |= previous_task
                    new_previous_tasks |= previous_task.previous_task_ids. \
                        filtered(lambda task: task not in planned_tasks and
                                 not (task.critical_task and not previous_task.critical_task))
                    new_next_tasks |= previous_task.next_task_ids. \
                        filtered(lambda task: task not in planned_tasks and
                                 not (task.critical_task and not previous_task.critical_task))
                for next_task in next_tasks:
                    previous_tasks_with_end_dates = self.env['project.task']. \
                        search([('id', 'in', next_task.previous_task_ids.ids), ('objective_end_date', '!=', False)])
                    objective_start_date = max([task.objective_end_date for task in previous_tasks_with_end_dates] or
                                               [False])
                    all_previous_tasks_on_start_day = \
                        previous_tasks_with_end_dates and all([task.objective_instant_task_start_day for
                                                               task in previous_tasks_with_end_dates]) or False
                    print 'next', next_task.name, objective_start_date, all_previous_tasks_on_start_day
                    if objective_start_date and not all_previous_tasks_on_start_day:
                        objective_start_date = next_task.schedule_get_date(objective_start_date, 1)
                    objective_end_date = objective_start_date and next_task.\
                        schedule_get_date(objective_start_date, next_task.objective_duration - 1) or False
                    vals_next_task = {
                        'objective_start_date': objective_start_date,
                        'objective_end_date': objective_end_date,
                        'objective_instant_task_start_day': not next_task.objective_duration,
                        'objective_instant_task_end_day': False,
                    }
                    print 'vals_next_task', vals_next_task
                    next_task.write(vals_next_task)
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
                print 'update_objective_dates_parent_tasks', parent_task.name, children_tasks
                if children_tasks:
                    min_objective_start_date = min([task.objective_start_date for
                                                    task in children_tasks if task.objective_start_date] or [False])
                    max_objective_end_date = max([task.objective_end_date for
                                                  task in children_tasks if task.objective_end_date] or [False])
                    objective_instant_task_start_day = all([task.objective_instant_task_start_day for
                                                            task in children_tasks])
                    objective_instant_task_end_day = all([task.objective_instant_task_end_day for
                                                          task in children_tasks])
                    parent_task.with_context(do_not_propagate_dates=True).write({
                        'objective_start_date': min_objective_start_date,
                        'objective_end_date': max_objective_end_date,
                        'objective_instant_task_start_day': objective_instant_task_start_day,
                        'objective_instant_task_end_day': objective_instant_task_end_day,
                    })

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
    objective_end_date = fields.Date(string=u"Objective end date", readonly=True)
    objective_start_date = fields.Date(string=u"Objective start date")
    expected_start_date = fields.Date(string=u"Expected start date", index=True)
    expected_end_date = fields.Date(string=u"Expected end date", index=True)
    objective_instant_task_start_day = fields.Boolean(string=u"Null duration task in the morning")
    objective_instant_task_end_day = fields.Boolean(string=u"Null duration task in the evening")
    effective_instant_task_start_day = fields.Boolean(string=u"Null duration task in the morning")
    effective_instant_task_end_day = fields.Boolean(string=u"Null duration task in the evening")
    expected_start_date_display = fields.Datetime(string=u"Expected start date (display)",
                                                  compute='_compute_expected_start_date_display', store=True,
                                                  inverse='_set_expected_start_date_display')
    expected_end_date_display = fields.Datetime(string=u"Expected end date (display)",
                                                compute='_compute_expected_end_date_display', store=True,
                                                inverse='_set_expected_end_date_display')
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
    is_milestone = fields.Boolean(string="Is milestone", compute='_get_is_milestone', store=True, default=False)
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
            # TODO: à ré-écrire
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

    @api.multi
    @api.depends('expected_start_date')
    def _compute_expected_start_date_display(self):
        for rec in self:
            end_date_string = ' 08:00:00'
            if rec.effective_instant_task_end_day:
                end_date_string = ' 18:00:00'
            rec.expected_start_date_display = rec.expected_start_date and (rec.expected_start_date +
                                                                           end_date_string) or False

    @api.multi
    @api.depends('expected_end_date')
    def _compute_expected_end_date_display(self):
        for rec in self:
            end_date_string = ' 18:00:00'
            if rec.effective_instant_task_start_day:
                end_date_string = ' 08:00:00'
            rec.expected_end_date_display = rec.expected_end_date and (rec.expected_end_date +
                                                                       end_date_string) or False

    @api.multi
    def _set_expected_start_date_display(self):
        for rec in self:
            rec.expected_start_date = rec.expected_start_date_display and rec.expected_start_date_display[:10] or False

    @api.multi
    def _set_expected_end_date_display(self):
        for rec in self:
            rec.expected_end_date = rec.expected_end_date_display and rec.expected_end_date_display[:10] or False

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
            resource = self.env['resource.resource'].search([('user_id', '=', reference_user.id),
                                                             ('resource_type', '=', 'user')], limit=1)
        if not resource:
            resource = self.env['resource.resource'].search([('user_id', '=', self.env.user.id),
                                                             ('resource_type', '=', 'user')], limit=1)
        calendar = False
        if use_calendar:
            calendar = resource and resource.calendar_id or self.company_id.calendar_id or \
                self.env.ref('resource_improved.default_calendar')
        return resource, calendar

    @api.multi
    def schedule_get_date(self, date_ref, nb_days=0):
        """
        From a task (self), this function computes the date which is 'nb_days' days after day 'date_ref'.
        :param date_ref: fields.Date
        :param nb_days: Number of days to add/remove:
        :return fields.Date
        """
        self.ensure_one()
        target_date = fields.Date.from_string(date_ref)
        if nb_days:
            step = relativedelta(days=nb_days > 0 and 1 or -1)
            target_nb_working_days = abs(int(nb_days))
            nb_working_days = 0
            while nb_working_days < target_nb_working_days:
                target_date += step
                if self.is_working_day(target_date):
                    nb_working_days += 1
        return fields.Date.to_string(target_date)

    @api.multi
    def get_nb_working_hours_from_expected_dates(self):
        self.ensure_one()
        resource, calendar = self.get_default_calendar_and_resource()
        nb_days = 0
        nb_hours = 0
        if self.expected_start_date and self.expected_end_date:
            if self.expected_start_date == self.expected_end_date:
                nb_days = 1
            else:
                nb_hours = calendar.get_working_hours(fields.Datetime.from_string(self.expected_start_date),
                                                      fields.Datetime.from_string(self.expected_end_date),
                                                      compute_leaves=True, resource_id=resource.id)
            nb_hours = nb_hours and nb_hours[0] or 0
        else:
            nb_days = self.objective_duration
        return nb_days, nb_hours

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
            if expected_start_date and not rec.is_working_day(fields.Date.from_string(expected_start_date)):
                raise UserError(_(u"Task %s: impossible to set start date in a not working period (%s)") %
                                (rec.display_name, expected_start_date))
            if expected_end_date and not rec.is_working_day(fields.Date.from_string(expected_end_date)):
                raise UserError(_(u"Task %s: impossible to set end date in a not working period (%s)") %
                                (rec.display_name, expected_end_date))

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
    def schedule_tasks_after_end_date(self, end_date):
        for rec in self:
            expected_start_date = end_date
            if not rec.effective_instant_task_end_day:
                expected_start_date = rec.schedule_get_date(end_date, 1)
            task_data = {'expected_start_date': expected_start_date}
            if not rec.children_task_ids:
                # If rec has children, children planification will reschedule its end date if needed
                expected_end_date = expected_start_date
                if not rec.effective_instant_task_start_day:
                    nb_working_days = rec.get_task_number_open_days()
                    expected_end_date = rec.schedule_get_date(expected_start_date, nb_working_days - 1)
                task_data['expected_end_date'] = expected_end_date
            rec.write(task_data)

    @api.multi
    def schedule_tasks_before_start_date(self, start_date):
        for rec in self:
            expected_end_date = start_date
            if not rec.effective_instant_task_start_day:
                expected_end_date = rec.schedule_get_date(start_date, -1)
            task_data = {'expected_end_date': expected_end_date}
            if not rec.children_task_ids:
                # If rec has children, children planification will reschedule its start date if needed
                expected_start_date = expected_end_date
            if not rec.effective_instant_task_start_day:
                nb_working_days = rec.get_task_number_open_days()
                expected_start_date = rec.schedule_get_date(expected_end_date, -nb_working_days + 1)
                task_data['expected_start_date'] = expected_start_date
            rec.write(task_data)

    @api.multi
    def check_dates(self):
        self.check_expected_dates_consistency()
        self.check_dates_consistency_with_parents()
        self.check_dates_consistency_with_children()

    @api.multi
    def propagate_dates(self):
        self.ensure_one()
        next_tasks_to_reschedule = self.env['project.task']
        if self.expected_end_date:
            for task in self.next_task_ids:
                if not task.expected_start_date:
                    next_tasks_to_reschedule |= task
                    continue
                if self.expected_end_date == task.expected_start_date and task.effective_instant_task_end_day:
                    continue
                if self.expected_end_date >= task.expected_start_date:
                    next_tasks_to_reschedule |= task
        next_tasks_to_reschedule.schedule_tasks_after_end_date(self.expected_end_date)
        previous_tasks_to_reschedule = self.env['project.task']
        if self.expected_start_date:
            for task in self.previous_task_ids:
                if not task.expected_end_date:
                    previous_tasks_to_reschedule |= task
                    continue
                if self.expected_start_date == task.expected_end_date and task.effective_instant_task_start_day:
                    continue
                if self.expected_start_date <= task.expected_end_date:
                    previous_tasks_to_reschedule |= task
        previous_tasks_to_reschedule.schedule_tasks_before_start_date(self.expected_start_date)
        for task in self.env['project.task'].search([
            ('id', 'child_of', self.children_task_ids.ids),
            ('expected_end_date', '>', self.expected_end_date),
            '|', ('next_task_ids', '=', False),
            ('next_task_ids.parent_task_id', '!=', self.id),
        ], order='expected_end_date desc'):
            if task.expected_end_date >= self.expected_start_date:
                print 'schedule_tasks_after_end_date', task.name, self.expected_start_date
                task.schedule_tasks_after_end_date(self.expected_end_date)
        for task in self.env['project.task'].search([
            ('id', 'child_of', self.children_task_ids.ids),
            ('expected_start_date', '<', self.expected_start_date),
            '|', ('previous_task_ids', '=', False),
            ('previous_task_ids.parent_task_id', '!=', self.id),
        ], order='expected_start_date asc'):
            print 'schedule_tasks_before_start_date', task.name, self.expected_start_date
            if task.expected_start_date <= self.expected_start_date:
                task.schedule_tasks_before_start_date(self.expected_start_date)
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
    def set_tasks_not_instant_if_required(self, vals):
        if vals.get('expected_start_date_display') and vals.get('expected_end_date_display'):
            for rec in self:
                if vals.get('expected_start_date_display',
                            rec.expected_start_date_display) != vals.get('expected_end_date_display',
                                                                         rec.expected_end_date_display):
                    rec.with_context(do_not_propagate_dates=True).write({'effective_instant_task_start_day': False,
                                                                         'effective_instant_task_end_day': False})

    @api.multi
    def write(self, vals):
        self.set_tasks_not_instant_if_required(vals)
        if 'objective_end_date' in vals:
            _logger.info(u"Scheduling task(s) %s for objective end date %s", u",".join([rec.name for rec in self]),
                         vals.get('objective_end_date'))
        dates_changed = (vals.get('expected_start_date') or vals.get('expected_end_date')) and True or False
        propagate_dates = not self.env.context.get('do_not_propagate_dates')
        print 'write', [(rec.id, rec.name) for rec in self], vals, propagate_dates, dates_changed
        propagating_tasks = self.env.context.get('propagating_tasks')
        slide_tasks = self.get_slide_tasks(vals)
        for rec in self:
            # if rec.name == u'Parent task 4' and vals.get('expected_end_date') == '2017-10-16':
            #     1/0
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
                print 'propagate_dates'
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
             rml_obj.formatLang(self.expected_start_date, date=True),
             rml_obj.formatLang(self.expected_end_date, date=True))

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
        # TODO: à retirer
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
            list_intervals = calendar.get_working_intervals_of_day(start_dt=dt(date.year, date.month, date.day),
                                                                   compute_leaves=True,
                                                                   resource_id=resource and resource.id or False)
        return list_intervals and list_intervals[0] and True or False

    @api.multi
    def get_task_number_open_days(self):
        self.ensure_one()
        open_days = 0
        start = fields.Date.from_string(self.expected_start_date)
        end = fields.Date.from_string(self.expected_end_date)
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
                ref_date = fields.Date.from_string(min_date)
                max_date = fields.Date.from_string(max_date)
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
