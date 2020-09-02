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
from odoo import models, fields, api


class ProjectTaskCoefficient(models.Model):
    _name = 'project.task.coefficient'

    name = fields.Char(u"Name", required=True)
    coefficient = fields.Float(u"Coefficient", required=True)
    active = fields.Boolean(u"Active", default=True)
    project_id = fields.Many2one('project.project', string="Projet")

    @api.multi
    def name_get(self):
        return [(rec.id, u"%s (%s)" % (rec.name, rec.coefficient)) for rec in self]


class ProjectTask(models.Model):
    _inherit = 'project.task'

    coefficient_ids = fields.Many2many('project.task.coefficient', string=u"Coefficient")
    time_with_coefficient = fields.Float(string=u"Time with coefficient", compute="_compute_calculate_time")
    time_with_coefficient_rounded = fields.Float(string=u"Time with coefficient rounded",
                                                 compute="_compute_calculate_time")
    time_open = fields.Float(string=u"Time open wrote by product manager")
    time_free = fields.Float(string=u"Time free")
    time_free_comment = fields.Text(string=u"Comment about time free")

    @api.multi
    @api.onchange('coefficient_ids')
    def _compute_calculate_time(self):
        for rec in self:
            sum_diff = 1
            for coefficient_id in rec.coefficient_ids:
                sum_diff = coefficient_id.coefficient * sum_diff
            rec.time_with_coefficient = (rec.planned_days * sum_diff)
            rec.time_with_coefficient_rounded = round((rec.planned_days * sum_diff) * 4) / 4


class ProjectProject(models.Model):
    _inherit = 'project.project'

    coefficient_ids = fields.One2many('project.task.coefficient', 'project_id')
