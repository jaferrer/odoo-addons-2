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
from odoo import models


class MrpProductionPortal(models.Model):
    _inherit = 'mrp.production'

    # @api.multi
    # def get_formview_id(self):
    #     user_id = self.env.context.get('uid')
    #     user = user_id and self.env['res.users'].browse(user_id) or self.env.user
    #     if user.has_group('base.group_portal'):
    #         return self.env.ref('mrp_portal.view_mrp_portal_mrp_production_form').id
    #     return super(MrpProductionPortal, self).get_formview_id()
