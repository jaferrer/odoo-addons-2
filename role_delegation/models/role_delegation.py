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


class RoleDelegation(models.Model):
    _name = 'res.users.role.delegation'
    _description = u"Role delegation"

    user_id = fields.Many2one('res.users', u"User", required=True)
    target_id = fields.Many2one('res.users', u"Target user", required=True)
    date_from = fields.Date(u"From", required=True)
    date_to = fields.Date(u"To", required=True)
    role_line_ids = fields.Many2many('res.users.role.line')

    _sql_constraints = [
        (
            'date_order',
            "CHECK(date_from <= date_to)",
            u"The ending date must be later than or equal to the starting date."
        )
    ]

    @api.model
    def create(self, vals):
        original_user = self.env['res.users'].browse(vals.get('user_id'))
        user_roles = original_user.mapped('role_line_ids.role_id')
        new_role_lines = []
        for role in user_roles:
            new_role_lines.append((0, 0, {
                'user_id': vals.get('target_id'),
                'role_id': role.id,
                'date_from': vals.get('date_from'),
                'date_to': vals.get('date_to'),
            }))
        vals['role_line_ids'] = new_role_lines

        res = super(RoleDelegation, self).create(vals)
        res.target_id.sudo().set_groups_from_roles()
        return res

    @api.multi
    def write(self, vals):
        if 'date_from' in vals or 'date_to' in vals:
            for rec in self:
                rec.role_line_ids.write({
                    'date_from': vals.get('date_from', rec.date_from),
                    'date_to': vals.get('date_to', rec.date_to),
                })
        self.mapped('target_id').sudo().set_groups_from_roles()

        return super(RoleDelegation, self).write(vals)

    @api.multi
    def unlink(self):
        self.mapped('role_line_ids').unlink()
        return super(RoleDelegation, self).unlink()
