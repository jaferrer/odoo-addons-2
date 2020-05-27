# -*- coding: utf8 -*-
#
# Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

    item_ids = fields.One2many('project.task.item', 'task_id', u"Items")
    planned_hours_amount = fields.Float(u"Time estimated", compute='_compute_planned_hours_amount',
                                        help=u"Computed using the sum of the todo's initially planned hours")
    is_todo_visible_portal = fields.Boolean(compute='_compute_is_todo_visible_portal')

    @api.multi
    def _compute_planned_hours_amount(self):
        for rec in self:
            rec.planned_hours_amount = sum(item.planned_hours for item in rec.item_ids)

    @api.multi
    def _compute_is_todo_visible_portal(self):
        for rec in self:
            rec.is_todo_visible_portal = any(item.is_visible_portal for item in rec.item_ids)


class ProjectTaskItem(models.Model):
    _name = 'project.task.item'
    _order = 'sequence, id'

    task_id = fields.Many2one('project.task', u"Task")
    is_visible_portal = fields.Boolean(u"Visible Portal")
    done = fields.Boolean(u"Done")
    description = fields.Char(u"Content", required=True)
    sequence = fields.Integer(u"Sequence")
    planned_hours = fields.Float(
        u"Initially Planned Hours",
        help=u"Estimated time to do the task, usually set by the project manager when the task is in draft state.")

    @api.multi
    def toggle_done(self):
        for rec in self:
            rec.done = not rec.done
