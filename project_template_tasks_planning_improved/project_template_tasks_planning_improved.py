# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api


class PlanningImprovedTemplateTaskType(models.Model):
    _inherit = 'project.task.type'

    @api.multi
    def get_values_new_task(self, task, project):
        result = super(PlanningImprovedTemplateTaskType, self).get_values_new_task(task, project)
        result['next_task_ids'] = False
        result['previous_task_ids'] = False
        return result

    @api.multi
    def synchronize_default_tasks(self):
        result = super(PlanningImprovedTemplateTaskType, self).synchronize_default_tasks()
        project_id = self.env.context.get('project_id')
        for rec in self:
            for generated_task in result[rec]:
                new_vals_for_generated_task = {}
                template_task = generated_task.generated_from_template_id
                previous_template_tasks = template_task.previous_task_ids
                next_template_tasks = template_task.next_task_ids
                previous_tasks = self.env['project.task']
                next_tasks = self.env['project.task']
                for previous_template_task in previous_template_tasks:
                    previous_tasks |= previous_template_task.find_generated_task_for_template(project_id)
                for next_template_task in next_template_tasks:
                    next_tasks |= next_template_task.find_generated_task_for_template(project_id)
                if previous_tasks and generated_task.previous_task_ids != previous_tasks:
                    new_vals_for_generated_task['previous_task_ids'] = [(6, 0, previous_tasks.ids)]
                if next_tasks and generated_task.next_task_ids != next_tasks:
                    new_vals_for_generated_task['next_task_ids'] = [(6, 0, next_tasks.ids)]
                template_parent_task = template_task.parent_task_id
                if template_parent_task:
                    parent_task = template_parent_task.find_generated_task_for_template(project_id)
                    if parent_task:
                        new_vals_for_generated_task['parent_task_id'] = parent_task.id
                if new_vals_for_generated_task:
                    generated_task.write(new_vals_for_generated_task)
        return result
