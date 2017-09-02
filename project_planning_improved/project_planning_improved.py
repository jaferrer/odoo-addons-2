# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api, fields, _


class ProjectImprovedProject(models.Model):
    _inherit = 'project.project'

    @api.multi
    def open_task_planning(self):
        self.ensure_one()
        view = self.env.ref('project_planning_improved.project_improved_task_tree')
        ctx = self.env.context.copy()
        ctx['search_default_project_id'] = self.id
        return {
            'name': _("Tasks planning for project %s") % self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'project.task',
            'views': [(view.id, 'tree')],
            'view_id': view.id,
            'context': ctx,
        }


class ProjectImprovedTask(models.Model):
    _inherit = 'project.task'

    parent_task_id = fields.Many2one('project.task', string=u"Parent task")
    previous_task_ids = fields.Many2many('project.task', 'project_task_order_rel', 'next_task_id',
                                         'previous_task_id', string=u"Previous tasks")
    next_task_ids = fields.Many2many('project.task', 'project_task_order_rel', 'previous_task_id',
                                     'next_task_id', string=u"Next tasks")
