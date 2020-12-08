# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class ResUsersAssignment(models.Model):
    """ This model circumvents company domains to allow assignments.

    Normally when using a multi company setup, you are restricted to seeing
    only records owned by the company your user is operating under
    (`user.company_id`). This creates a catch 22 with multi-company records,
    because in order to assign to another company you have to be able to view
    that company.
    """

    _name = 'res.users.assignment'
    _description = u"Users"
    _auto = False

    name = fields.Char(string=u"Name")
    partner_id = fields.Many2one('res.partner', string=u"Partner")

    @api.model_cr
    def init(self):

        self.env.cr.execute("""
        CREATE OR REPLACE VIEW res_users_assignment AS (
select res_users.id, res_partner.name, res_partner.id as partner_id
from res_users
         left join res_partner ON res_users.partner_id = res_partner.id
        )""")
