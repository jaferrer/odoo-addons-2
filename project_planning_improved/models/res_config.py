# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api


class ProjectPlanningImprovedSettings(models.TransientModel):
    _inherit = 'project.config.settings'

    notify_date_changes_for_partner_ids = fields. \
        Many2many('res.partner',
                  string=u"Partners to notify for date modifications in tasks",
                  help=u"Only for tasks flaged as 'notify managers when dates change'")

    @api.multi
    def get_default_notify_date_changes_for_partner_ids(self):
        value = self.env['ir.config_parameter'].get_param('project_planning_improved.notify_date_changes_for_partner_ids',
                                                          default='[]')
        return {'notify_date_changes_for_partner_ids': value and eval(value) or False}

    @api.multi
    def set_notify_date_changes_for_partner_ids(self):
        for record in self:
            self.env['ir.config_parameter'].set_param('project_planning_improved.notify_date_changes_for_partner_ids',
                                                      record.notify_date_changes_for_partner_ids and
                                                      str(record.notify_date_changes_for_partner_ids.ids) or '[]')
