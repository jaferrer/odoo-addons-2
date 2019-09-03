# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class ProjectTask(models.Model):
    _inherit = 'project.task'

    is_template_task = fields.Boolean(u"Is template task", help=u"Use to create sub task from this", default=False)
    template_task_id = fields.Many2one('project.task', u"Template task", domain=[('is_template_task', '=', True)])
    children_task_ids = fields.One2many('project.task', 'template_task_id', u"Children tasks",
                                        domain=[('is_template_task', '=', False)])
    duration = fields.Float(u"Spacing the task in days", compute='_get_duration', store=True, digits=(8, 2))
    duration_per_day = fields.Float(u"Durée de la tâche par jour", help=u"In hours", compute='_get_duration',
                                    store=True, digits=(8, 2))

    @api.depends('date_start', 'date_end', 'planned_hours')
    @api.multi
    def _get_duration(self):
        for rec in self:
            date_start = fields.Datetime.from_string(rec.date_start)
            date_end = fields.Datetime.from_string(rec.date_end)
            if date_start and date_end:
                rec.duration = (date_end - date_start).days or 1
            if rec.duration and rec.planned_hours:
                rec.duration_per_day = rec.planned_hours / (rec.duration * 1.0)
