# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class ProjectTaskTypeGitLab(models.Model):
    _inherit = 'project.task.type'

    project_id = fields.Many2one(
        'project.project',
        string=u"Project",
        compute='_get_project_id',
        inverse='_set_project_id',
        store=True)

    @api.multi
    def _set_project_id(self):
        for rec in self:
            rec.project_ids = [(6, 0, [rec.project_id.id])]

    @api.multi
    def _get_project_id(self):
        for rec in self:
            rec.project_id = rec.project_ids and rec.project_ids[0] or False


class ProjectProject(models.Model):
    _inherit = 'project.project'

    task_type_ids = fields.One2many(
        'project.task.type',
        'project_id',
        string=u"Project Stage"
    )


class ProjectTags(models.Model):
    _inherit = 'project.tags'

    project_id = fields.Many2one('project.project', u"Project")
    active = fields.Boolean(u"Actif", default=True)
