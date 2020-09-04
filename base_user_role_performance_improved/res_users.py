# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import api, models


class ResUsersRole(models.Model):
    _inherit = 'res.users.role'

    @api.multi
    def write(self, vals):
        for role in self:
            new_vals = dict(vals)
            if 'group_id' in new_vals and new_vals['group_id'] == role.group_id.id:
                new_vals.pop('group_id')
            if 'implied_ids' in new_vals:
                new_implied_ids = vals['implied_ids']
                if isinstance(new_implied_ids, list) and len(new_implied_ids) == 1:
                    new_implied_ids_tuple = new_implied_ids[0]
                    if len(new_implied_ids_tuple) == 3 and \
                            new_implied_ids_tuple[0] == 6 and \
                            isinstance(new_implied_ids_tuple[2], list):
                        new_implied_group_ids = new_implied_ids_tuple[2]
                        if set(new_implied_group_ids) == set(role.implied_ids.ids):
                            new_vals.pop('implied_ids')
            if 'group_id' not in new_vals and 'implied_ids' not in new_vals:
                super(ResUsersRole, role.with_context(do_not_set_groups_from_roles=True)).write(new_vals)
            else:
                super(ResUsersRole, role).write(new_vals)
        return True


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.multi
    def set_groups_from_roles(self):
        if self.env.context.get('do_not_set_groups_from_roles'):
            return True
        return super(ResUsers, self).set_groups_from_roles()
