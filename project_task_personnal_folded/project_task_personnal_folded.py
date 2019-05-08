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


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    folded = fields.Boolean(compute='_compute_folded', inverse='_inverse_folded')

    @api.multi
    def _compute_folded(self):
        for rec in self:
            rec.folded = self.env['project.task.category.folded'].search([
                ('category_id', '=', rec.id),
                ('user_id', '=', self.env.user)
            ]).folded

    @api.multi
    def _inverse_folded(self):
        for rec in self:
            existing = self.env['project.task.category.folded'].search([
                ('category_id', '=', rec.id),
                ('user_id', '=', self.env.user)
            ])
            data = {
                'folded': rec.folded,
                'category_id': rec.id,
                'user_id': self.env.user.id
            }
            if existing:
                existing.write(data)
            else:
                self.env['project.task.category.folded'].create(data)


class ProjectTaskTypeFolded(models.Model):
    _name = 'project.task.type.folded'

    user = fields.Many2one('res.users', u"User")
    amount_days = fields.Many2one('project.task.category', u"Category")
    folded = fields.Boolean(u"Fold")
