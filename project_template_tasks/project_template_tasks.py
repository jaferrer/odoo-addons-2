# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from openerp import tools
from openerp.exceptions import UserError


class ProjectTemplateProject(models.Model):
    _inherit = 'project.project'

    def _get_default_task_type_ids(self):
        default_types = self.env['project.task.type'].search([('use_default_for_all_projects', '=', True)])
        return default_types and default_types.ids or False

    use_task_type_ids = fields.Many2many('project.task.type', 'project_task_type_rel', 'project_id', 'type_id',
                                         string="Project Task Types", default=_get_default_task_type_ids)

    @api.multi
    def synchronize_default_tasks(self):
        for rec in self:
            rec.use_task_type_ids.with_context(project_id=rec.id).synchronize_default_tasks()


class ProjectTemplateTask(models.Model):
    _inherit = 'project.task'

    is_template = fields.Boolean(string="Template task")


class ProjectTemplateTaskType(models.Model):
    _inherit = 'project.task.type'

    use_default_for_all_projects = fields.Boolean(string="Default use for all projects")
    task_ids = fields.One2many('project.task', 'stage_id', string="Default tasks for this type",
                               domain=[('is_template', '=', True)])

    @api.multi
    def get_values_new_task(self, task, project):
        self.ensure_one()
        return {'name': task.name,
                'is_template': False,
                'project_id': project.id,
                'stage_id': self.id,
                'user_id': project.user_id and project.user_id.id or False,
                'date_start': False}

    @api.multi
    def synchronize_default_tasks(self):
        project_id = self.env.context.get('project_id')
        if project_id:
            project = self.env['project.project'].browse(project_id)
            for rec in self:
                if project.tasks.filtered(lambda task: task.stage_id == rec):
                    raise UserError(_("Forbidden to overwrite tasks of type %s") % rec.name)
                for task in rec.task_ids:
                    vals_copy = rec.get_values_new_task(task, project)
                    task.copy(vals_copy)


class ProjectTemplateTaskReport(models.Model):
    _inherit = 'report.project.task.user'

    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'report_project_task_user')
        cr.execute("""
            CREATE view report_project_task_user as
              %s
              FROM project_task t
                WHERE t.active = 'true' AND (t.is_template IS FALSE OR t.is_template IS NULL OR t.is_template = 'false')
                %s
        """ % (self._select(), self._group_by()))
