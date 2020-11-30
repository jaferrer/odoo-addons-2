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

from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = ['mail.thread', 'res.users']
    _name = 'res.users'

    delegation_ids = fields.One2many('res.users.role.delegation', 'user_id', u"Role delegations")
    allowed_user_ids = fields.Many2many('res.users', u"Users replaced by this user",
                                        compute='_compute_allowed_user_ids')
    received_delegation_ids = fields.One2many('res.users.role.delegation', 'target_id', u"Received delegations",
                                              readonly=True)

    @api.multi
    def _compute_allowed_user_ids(self):
        for rec in self:
            if rec.id == self.env.ref('base.user_root').id:
                rec.allowed_user_ids = self.env['res.users'].search([])
            else:
                rec.allowed_user_ids = rec | self.env['res.users.role.delegation'].search([
                    ('target_id', '=', rec.id),
                    ('date_from', '<=', fields.Date.today()),
                    ('date_to', '>=', fields.Date.today()),
                ]).mapped('user_id')

    @api.multi
    def get_allowed_users(self, candidates):
        """ Return all users that the current user replaces in a recordset of users

        :param candidates: a recordset of res.users
        :return: subset of candidates that are the current user or represented by them
        """
        self.ensure_one()
        return candidates & self.allowed_user_ids
