# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
import sys
from openerp import models, api


class ir_actions_act_window(models.Model):
    _inherit = 'ir.actions.act_window'

    @api.multi
    def open_act_window_tree_view(self):
        self.ensure_one()
        menu = self.env['ir.ui.menu'].search([('action', '=', self.id)], limit=1)
        menu_id = menu and menu.id or ""
        url = "/web?#page=0&limit=80&view_type=list&model=%s&menu_id=%s&action=%s" % (self.res_model, menu_id, self.id)
        return {
                "type": "ir.actions.act_url",
                "url": url,
                "target": "self"
        }
