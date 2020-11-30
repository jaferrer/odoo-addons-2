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


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    fold = fields.Boolean(
        "Fold",
        compute='_compute_fold',
        inverse='_inverse_fold',
        search='_search_fold'
    )

    fold_by_user_ids = fields.One2many('project.task.type.fold', 'task_type_id')

    @api.multi
    def dummy_save(self):
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def _compute_fold(self):
        self_ctx = self
        # Compute trigger as sudo or we want the real user behind the compute
        if self.env.user == self.sudo().env.user and self.env.context.get('uid'):
            self_ctx = self.sudo(self.env.context.get('uid'))
        for rec in self:
            domain = [('task_type_id', '=', rec.id)]
            mines = self_ctx.env['project.task.type.fold'].search(domain + [('user_id', '=', self_ctx.env.user.id)])
            everybody = self_ctx.env['project.task.type.fold'].search(domain + [('user_id', '=', False)])

            rec.fold = mines and mines[0].folded or everybody and everybody[0].folded or False

    @api.multi
    def _inverse_fold(self):
        for rec in self:
            mine = rec.fold_by_user_ids.filtered(lambda it: it.user_id)
            if not mine:
                mine = self.env['project.task.type.fold'].create({
                    'task_type_id': rec.id,
                    'user_id': self.env.user.id,
                })
            mine[0].folded = rec.fold

    @api.model
    def _search_fold(self, operator, operand):
        domain = [('folded', operator, not operand)]
        params = self.env.context.get('params', {})
        if params.get('model') == 'project.project' and params.get('id'):
            domain += [('task_type_id.project_id', '=', params.get('id'))]
        mines_inverse = self.env['project.task.type.fold'].search(domain + [('user_id', '=', self.env.user.id)])
        if not mines_inverse:
            return []
        return [('id', 'not in', mines_inverse.mapped('task_type_id').ids)]


class ProjectTaskTypeFold(models.Model):
    _name = 'project.task.type.fold'

    task_type_id = fields.Many2one('project.task.type', u"Step")
    user_id = fields.Many2one('res.users', u"User")
    folded = fields.Boolean(u"Folded")
