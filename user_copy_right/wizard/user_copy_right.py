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

from openerp import api, fields, models, _


class UserCopyRights(models.TransientModel):
    _name = 'user.copy.rights'

    user_model_id = fields.Many2one('res.users', string=u"User template")
    group_ids = fields.Many2many('res.groups', string=u"Groups", related='user_model_id.groups_id', readonly=True)
    user_ids = fields.Many2many('res.users', string=u"Users to modify")

    @api.multi
    def validate(self):
        self.ensure_one()
        self.user_ids.write({
            'groups_id': [(6, False, self.user_model_id.groups_id.ids)],
            'company_ids': [(6, False, self.user_model_id.company_ids.ids)]
        })
        return {
            'name': _(u"Users"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'res.users',
            'domain': [('id', 'in', self.user_ids.ids)],
            'context': self.env.context,
            'target': 'current'
        }
