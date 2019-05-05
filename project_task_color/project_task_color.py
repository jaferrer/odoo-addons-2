# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class ProjectTaskColor(models.Model):
    _name = 'project.task.color'
    _order = 'sequence'

    project_id = fields.Many2one('project.project', u"Project")
    sequence = fields.Integer(u"Sequence")
    category_id = fields.Many2one(
        'project.task.category',
        u"Category",
        domain="[('project_id', '=', project_id)]"
    )
    user_id = fields.Many2one('res.users', u"User")
    color = fields.Integer(u"Index of the color")


class ProjectProject(models.Model):
    _inherit = 'project.project'

    task_color_ids = fields.One2many('project.task.color', 'project_id', u"Colors of the Tasks")

    @api.multi
    def _compute_color(self, user=None, category=None):
        self.ensure_one()
        colors = False
        if category and user:
            colors = self.env['project.task.color'].search([
                ('project_id', '=', self.id),
                ('user_id', '=', user.id),
                ('category_id', '=', category.id)
            ])
        if not colors and user:
            colors = self.env['project.task.color'].search([
                ('project_id', '=', self.id),
                ('user_id', '=', user.id),
                ('category_id', '=', False)
            ])
        if not colors and category:
            colors = self.env['project.task.color'].search([
                ('project_id', '=', self.id),
                ('user_id', '=', False),
                ('category_id', '=', category.id)
            ])
        colors = colors or self.env['project.task.color'].search([
            ('project_id', '=', self.id),
            ('user_id', '=', False),
            ('category_id', '=', False)
        ])
        return colors and colors.color


class ProjectTask(models.Model):
    _inherit = 'project.task'

    color = fields.Integer(compute='_compute_color', inverse='_inverse_compute_color')
    force_color = fields.Integer(u"Forced Color")

    @api.multi
    def _compute_color(self):
        for rec in self:
            rec.color = rec.force_color or rec.project_id._compute_color(rec.create_uid, rec.category_id)

    @api.multi
    def _inverse_compute_color(self):
        for rec in self:
            rec.force_color = rec.color
