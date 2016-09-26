# -*- coding: utf8 -*-
#
#    Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api, _


class ProjectTask(models.Model):
    _inherit = "project.task"

    issue_ids = fields.One2many('project.issue', 'task_id', string=u"Issues")
    tag_ids = fields.Many2many('project.tags',
                               domain="['|', ('project_id', '=', False), ('project_id', '=', project_id)]")

    @api.multi
    def write(self, vals):
        # Sync child issues stage with task stage on stage change.
        if 'stage_id' in vals:
            for rec in self:
                rec.issue_ids.write({'stage_id': vals['stage_id']})
        return super(ProjectTask, self).write(vals)


class ProjectIssue(models.Model):
    _inherit = "project.issue"

    tag_ids = fields.Many2many('project.tags',
                               domain="['|', ('project_id', '=', False), ('project_id', '=', project_id)]")


class ProjectTags(models.Model):
    _inherit = "project.tags"

    project_id = fields.Many2one('project.project', string="Project")

    _sql_constraints = [
        ('name_uniq', 'unique (name,project_id)', _("Tag name already exists for this project!")),
    ]
