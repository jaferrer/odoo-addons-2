# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from odoo import models, tools, fields


class IrValues(models.Model):
    _inherit = 'ir.values'

    @tools.ormcache_context('self._uid', 'action_slot', 'model', 'res_id', keys=('lang',))
    def get_actions(self, action_slot, model, res_id=False):
        user = self.env['res.users'].browse(self._uid)
        res = super(IrValues, self).get_actions(action_slot, model, res_id)
        filtered_result = []
        for id, name, action_def in res:
            groups_id = action_def.get('groups_id', [])
            if not groups_id or any([group_id in user.groups_id.ids for group_id in groups_id]):
                filtered_result.append((id, name, action_def))
        return filtered_result


class ActServer(models.Model):
    _inherit = 'ir.actions.server'

    groups_id = fields.Many2many('res.groups', string=u"Groups")


class ActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    groups_id = fields.Many2many('res.groups', string=u"Groups")


class ActReport(models.Model):
    _inherit = 'ir.actions.report.xml'

    groups_id = fields.Many2many('res.groups', string=u"Groups")
