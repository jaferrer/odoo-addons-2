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

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class RoleDelegation(models.Model):
    _name = 'res.users.role.delegation'
    _description = u"Role delegation"

    user_id = fields.Many2one('res.users', u"User", required=True)
    target_id = fields.Many2one('res.users', u"Target user", required=True)
    date_from = fields.Date(u"From", required=True)
    date_to = fields.Date(u"To", required=True)
    role_id = fields.Many2one('res.users.role', u"Delegated role (all if left blank)")
    role_line_ids = fields.Many2many('res.users.role.line')
    allowed_role_ids = fields.Many2many('res.users.role', compute='_compute_allowed_role_ids')

    _sql_constraints = [
        (
            'date_order',
            "CHECK(date_from <= date_to)",
            u"The ending date must be later than or equal to the starting date."
        )
    ]

    @api.multi
    @api.constrains('user_id', 'role_id')
    def _constrains_role_id(self):
        for rec in self:
            if rec.role_id:
                role_line = self.env['res.users.role.line'].search([
                    ('user_id', '=', rec.user_id.id),
                    ('role_id', '=', rec.role_id.id),
                ], limit=1)
                if not role_line:
                    raise ValidationError(_(u"User %s hasn't got role %s") %
                                          (rec.user_id.display_name, rec.role_id.display_name))

    @api.multi
    @api.depends('user_id')
    def _compute_allowed_role_ids(self):
        for rec in self:
            rec.allowed_role_ids = rec.user_id.role_ids

    @api.multi
    @api.onchange('user_id')
    def onchange_user_id(self):
        user = self.env['res.users'].browse(self.user_id.id or self.env.context.get('default_user_id'))
        return {
            'domain': {
                'role_id': [('id', 'in', user.mapped('role_line_ids.role_id').ids)],
                'target_id': [('id', '!=', user.id)],
            }
        }

    @api.multi
    def _notify_user(self, template_xml_id):
        self.ensure_one()
        template = self.env.ref(template_xml_id)
        body = template.render({
            'obj': self.sudo()
        }).decode('utf-8')
        self.target_id.sudo().message_subscribe_users(user_ids=[self.target_id.id], subtype_ids=[
            self.env.ref('role_delegation.delegation_notification_subtype').id
        ])
        self.target_id.sudo().message_post(body=body, subtype='role_delegation.delegation_notification_subtype')

    @api.multi
    def _create_role_lines(self, user_id, target_id, date_from, date_to, role_id):
        role_ids = role_id and [role_id] or\
            self.env['res.users.role.line'].search([('user_id', '=', user_id)]).mapped('role_id').ids
        res = []
        for cur_role_id in role_ids:
            res.append((0, 0, {
                'user_id': target_id,
                'role_id': cur_role_id,
                'date_from': date_from,
                'date_to': date_to,
            }))
        return res

    @api.model
    def create(self, vals):
        vals['role_line_ids'] = self._create_role_lines(
            vals.get('user_id'), vals.get('target_id'), vals.get('date_from'), vals.get('date_to'), vals.get('role_id'))
        res = super(RoleDelegation, self).create(vals)
        res.target_id.sudo().set_groups_from_roles()
        res._notify_user('role_delegation.role_delegation_creation_target_template')
        return res

    @api.multi
    def write(self, vals):
        for rec in self:
            rec_vals = dict(vals)
            if 'user_id' in vals or 'target_id' in vals or 'role_id' in vals:
                rec.role_line_ids.sudo().unlink()
                rec_vals['role_line_ids'] = [(5, 0)] + rec._create_role_lines(
                    vals.get('user_id', rec.user_id.id),
                    vals.get('target_id', rec.target_id.id),
                    vals.get('date_from', rec.date_from),
                    vals.get('date_to', rec.date_to),
                    vals.get('role_id', rec.role_id.id)
                )
                rec._notify_user('role_delegation.role_delegation_modification_target_template')
            elif 'date_from' in vals or 'date_to' in vals:
                rec.role_line_ids.write({
                    'date_from': vals.get('date_from', rec.date_from),
                    'date_to': vals.get('date_to', rec.date_to),
                })
                rec._notify_user('role_delegation.role_delegation_modification_target_template')
            super(RoleDelegation, rec).write(rec_vals)

        self.mapped('target_id').sudo().set_groups_from_roles()

        return True

    @api.multi
    def unlink(self):
        self.mapped('role_line_ids').sudo().unlink()
        return super(RoleDelegation, self).unlink()

    @api.multi
    def name_get(self):
        return [
            (rec.id, _(u"%s delegation from %s to %s") %
             (rec.role_id.display_name, rec.user_id.display_name, rec.target_id.display_name))
            for rec in self
        ]
