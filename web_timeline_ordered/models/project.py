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

from openerp import models, api, _
from openerp.exceptions import UserError


class ProjectTask(models.Model):
    _inherit = "project.task"

    @api.multi
    def write(self, vals):
        # prohibits the change of project of a task on the timeline view
        if self.env.context.get('params') and self.env.context.get('params').get(
                'view_type') == 'timeline' and 'project_id' in vals:
            for rec in self:
                if vals.get('project_id') != rec.project_id.id:
                    raise UserError(_(u"You are not allowed to change the project of the task"))
        return super(ProjectTask, self).write(vals)
