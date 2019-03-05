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


class ProjectPlanningImprovedResPartner(models.Model):
    _inherit = 'res.partner'

    has_internal_user = fields.Boolean(string=u"Is linked to an internal user", compute='_compute_has_internal_user',
                                       store=True)

    @api.depends('user_ids', 'user_ids.share')
    @api.multi
    def _compute_has_internal_user(self):
        for rec in self:
            rec.has_internal_user = rec.user_ids and any([not user.share for user in rec.user_ids])
