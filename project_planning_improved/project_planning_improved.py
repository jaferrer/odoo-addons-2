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

from openerp import models, fields, api, _


class ProjectImprovedProject(models.Model):
    _inherit = 'project.project'

    reference_task = fields.Many2one('project.task', string=u"Reference task")
    reference_task_end_date = fields.Datetime(string=u"Reference task end date")
    can_change_reference_task = fields.Boolean(string="Can change reference task", readonly=True,
                                               compute="_get_change_reference_task")

    @api.multi
    def _get_change_reference_task(self):
        print "self: %s " % self
        for rec in self:
            if 63 in self.env.user.groups_id.ids or 65 in rec.env.user.groups_id.ids or 74 in rec.env.user.groups_id.ids:
                rec.can_change_reference_task = True
            else:
                rec.can_change_reference_task = False

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
    def start_auto_planning(self):
        for rec in self:
            domain_tasks = [('project_id', '=', rec.id), ('previous_task_ids', '=', False)]
            latest_tasks = self.env['project.task'].search(domain_tasks)
            longest_ways_to_tasks = {task: {'tasks': task, 'nb_days': task.planned_days} for task in latest_tasks}
            while latest_tasks:
                new_tasks_to_proceed = self.env['project.task']
                for latest_task in latest_tasks:
                    new_tasks_to_proceed |= latest_task.next_task_ids
                    for next_task in latest_task.next_task_ids:
                        set_new_way = True
                        if next_task in longest_ways_to_tasks.keys():
                            old_duration_to_task = longest_ways_to_tasks[next_task]['nb_days']
                            new_duration_to_task = longest_ways_to_tasks[latest_task]['nb_days'] + next_task.planned_days
                            if new_duration_to_task <= old_duration_to_task:
                                set_new_way = False
                                # Case of two critical ways
                                if new_duration_to_task == old_duration_to_task:
                                    longest_ways_to_tasks[next_task]['tasks'] = longest_ways_to_tasks[next_task]['tasks'] + longest_ways_to_tasks[latest_task]['tasks']
                        if set_new_way:
                            longest_ways_to_tasks[next_task] = {
                                'tasks': longest_ways_to_tasks[latest_task]['tasks'] + next_task,
                                'nb_days': longest_ways_to_tasks[latest_task]['nb_days'] + next_task.planned_days
                            }
                latest_tasks = new_tasks_to_proceed
            critical_nb_days = max([longest_ways_to_tasks[task]['nb_days'] for task in longest_ways_to_tasks.keys()])
            critical_tasks = self.env['project.task']
            for task in longest_ways_to_tasks.keys():
                if longest_ways_to_tasks[task]['nb_days'] == critical_nb_days:
                    critical_tasks |= longest_ways_to_tasks[task]['tasks']
            not_critical_tasks = self.env['project.task'].search(domain_tasks + [('id', 'not in', critical_tasks.ids)])
            critical_tasks.write({'critical_task': True})
            not_critical_tasks.write({'critical_task': False})


class ProjectImprovedTask(models.Model):
    _inherit = 'project.task'

    parent_task_id = fields.Many2one('project.task', string=u"Parent task")
    previous_task_ids = fields.Many2many('project.task', 'project_task_order_rel', 'next_task_id',
                                         'previous_task_id', string=u"Previous tasks")
    next_task_ids = fields.Many2many('project.task', 'project_task_order_rel', 'previous_task_id',
                                     'next_task_id', string=u"Next tasks")
    critical_task = fields.Boolean(string=u"Critical task", readonly=True)
    planned_days = fields.Float(string=u"Initially Planned Days")
    children_task_ids = fields.One2many('project.task', 'parent_task_id', string="Children tasks")
    objective_start_date = fields.Datetime(string="Objective start date")
    exepected_start_date = fields.Datetime(string="Expected start date")
    objective_end_date = fields.Datetime(string=" Objective end date")
    exepected_end_date = fields.Datetime(string="Expected end date")
    allocated_time = fields.Integer(string="Allocated time")
    allocated_time_unit_tasks = fields.Integer(string="Allocated for unit tasks",
                                               compute="_get_allocated_time_unit_tasks")
    total_allocated_time = fields.Integer(string=u"Total allocated time", compute="_get_total_allocated_time",
                                          store=True)
    progress_state = fields.Selection(
        [('todo', u'To do'), ('inprogress', u'In progress'), ('completed', u'Completed'), ('cancelled', u'Cancelled')],
        string=u"State of progress", default='todo', required=True, track_visibility='onchange')

    @api.depends('children_task_ids.total_allocated_time')
    def _get_allocated_time_unit_tasks(self):
        for record in self:
            record.allocated_time_unit_tasks = sum(line.total_allocated_time for line in record.children_task_ids)

    @api.depends('allocated_time_unit_tasks', 'allocated_time')
    def _get_total_allocated_time(self):
        for rec in self:
            rec.total_allocated_time = rec.allocated_time + rec.allocated_time_unit_tasks

    @api.multi
    def set_to_do(self):
        for rec in self:
            rec.progress_state = "todo"

    @api.multi
    def set_in_progress(self):
        for rec in self:
            rec.progress_state = "inprogress"

    @api.multi
    def set_completed(self):
        for rec in self:
            rec.progress_state = "completed"

    @api.multi
    def set_cancelled(self):
        for rec in self:
            rec.progress_state = "cancelled"
