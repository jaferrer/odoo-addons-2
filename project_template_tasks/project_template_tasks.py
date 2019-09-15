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

import logging

from openerp import models, fields, api, _
from openerp import tools

_logger = logging.getLogger(__name__)


class ProjectTemplateProject(models.Model):
    _inherit = 'project.project'

    def _get_default_task_type_ids(self):
        default_types = self.env['project.task.type'].search([('use_default_for_all_projects', '=', True)])
        return [(0, 0, {'project_id': self.id, 'type_id': type.id}) for type in default_types]

    use_task_type_ids = fields.One2many('project.task.type.rel', 'project_id', string=u"Project Task Types",
                                        default=_get_default_task_type_ids)

    @api.multi
    def synchronize_default_tasks(self):
        for rec in self:
            rec.use_task_type_ids.with_context(project_id=rec.id).synchronize_default_tasks()

    @api.multi
    def get_task_types(self):
        self.ensure_one()
        return self.env['project.task.type'].browse([item.type_id.id for item in self.use_task_type_ids])

    @api.multi
    def add_task_types(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        ctx['default_project_id'] = self.id
        return {
            'name': _(u"Add a Task Type"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.add.task.types',
            'target': 'new',
            'context': ctx,
        }


class ProjectAddTaskTypes(models.TransientModel):
    _name = 'project.add.task.types'

    project_id = fields.Many2one('project.project', string=u"Project", required=True)
    use_task_type_ids = fields.Many2many('project.task.type', string=u"Project Task Types", required=True)

    @api.onchange('project_id')
    def onchange_project_id(self):
        self.ensure_one()
        existing_task_types = self.project_id.get_task_types()
        return {'domain': {'use_task_type_ids': [('id', 'not in', existing_task_types.ids)]}}

    @api.multi
    def add(self):
        self.ensure_one()
        existing_task_types = self.project_id.get_task_types()
        max_sequence = max([line.sequence for line in self.project_id.use_task_type_ids] or [0])
        for task_type in self.use_task_type_ids:
            if task_type in existing_task_types:
                continue
            self.env['project.task.type.rel'].create({'project_id': self.project_id.id,
                                                      'type_id': task_type.id,
                                                      'sequence': max_sequence})

class ProjectTaskTypeRel(models.Model):
    _name = 'project.task.type.rel'

    sequence = fields.Integer(string=u"Sequence")
    project_id = fields.Many2one('project.project', string=u"Project", required=True)
    type_id = fields.Many2one('project.task.type', string=u"Task Type", required=True)

    def init(self, cr):
        """Overwriten to change table project_task_type_rel to a classical model table"""
        cr.execute("""SELECT COLUMN_NAME
FROM information_schema.COLUMNS
WHERE TABLE_NAME = 'project_task_type_rel'
  AND column_name = 'id';""")
        result = cr.fetchall()
        if not result or not result[0]:
            # Add column ID
            cr.execute("""ALTER TABLE project_task_type_rel ADD COLUMN id INTEGER;""")
            # Fill column ID
            cr.execute("""WITH data AS (
  SELECT project_id,
         type_id,
         ROW_NUMBER()
         OVER () AS id
  FROM project_task_type_rel)

UPDATE project_task_type_rel
SET id = data.id
FROM data
WHERE data.project_id = project_task_type_rel.project_id
  AND data.type_id = project_task_type_rel.type_id;""")
            # Add primary key
            cr.execute("""ALTER TABLE project_task_type_rel ADD PRIMARY KEY (id);""")
            # Add sequence on column ID if needed
            cr.execute("""SELECT sequence_name
FROM information_schema.sequences
WHERE sequence_name LIKE 'project_task_type_rel%';""")
            result = cr.fetchall()
            if not result or not result[0]:
                cr.execute("""CREATE SEQUENCE project_task_type_rel_id_seq;""")
                # Get max ID to parameter sequence
                cr.execute("""SELECT max(id) + 1
    FROM project_task_type_rel;""")
                result = cr.fetchall()
                max_id = result and result[0] and result[0][0] or 0
                # Parameter next number for ID sequence
                cr.execute("""ALTER SEQUENCE project_task_type_rel_id_seq RESTART WITH %s;""", (max_id,))

    @api.multi
    def get_values_new_task(self, task, project):
        self.ensure_one()
        return {'name': task.name,
                'is_template': False,
                'project_id': project.id,
                'stage_id': self.type_id.id,
                'user_id': project.user_id and project.user_id.id or False,
                'date_start': False,
                'generated_from_template_id': task.id}

    @api.multi
    def synchronize_default_tasks(self):
        result = {}
        for rec in self:
            generated_tasks = self.env['project.task']
            tasks_for_stage = self.env['project.task'].search([('id', 'in', rec.project_id.tasks.ids),
                                                               ('stage_id', '=', rec.type_id.id)])
            if tasks_for_stage:
                result[rec.type_id] = tasks_for_stage
            else:
                nb_tasks = len(rec.type_id.task_ids)
                index = 0
                for task in rec.type_id.task_ids:
                    index += 1
                    vals_copy = rec.get_values_new_task(task, rec.project_id)
                    _logger.info(u"Generating task %s for project %s (%s/%s for stage %s)" %
                                 (task.display_name, rec.project_id.display_name, index, nb_tasks,
                                  rec.type_id.display_name))
                    generated_tasks |= task.with_context(mail_notrack=True).copy(vals_copy)
                result[rec.type_id] = generated_tasks
        return result


class ProjectTemplateTask(models.Model):
    _inherit = 'project.task'

    is_template = fields.Boolean(string="Template task")
    generated_from_template_id = fields.Many2one('project.task', string=u"Generated from template task",
                                                 domain=[('is_template', '=', True)], readonly=True)

    _sql_constraints = [
        ('is_template_project_id', 'check(not(is_template is true and project_id is not null))',
         _(u"Impossible to attach a template task to a project.")),
    ]

    @api.multi
    def find_generated_task_for_template(self, project_id):
        self.ensure_one()
        assert self.is_template, u"Impossible to find generated task for a not-template task"
        return self.env['project.task']. \
            search([('project_id', '=', project_id),
                    ('generated_from_template_id', '=', self.id)])


class ProjectTemplateTaskType(models.Model):
    _inherit = 'project.task.type'

    use_default_for_all_projects = fields.Boolean(string="Default use for all projects")
    task_ids = fields.One2many('project.task', 'stage_id', string="Default tasks for this type",
                               domain=[('is_template', '=', True)])


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
