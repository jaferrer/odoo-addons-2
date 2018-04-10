# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.onchange('zip', 'country_id')
    def onchange_state_id(self):
        for rec in self:
            fr_countries = self.env['res.country'].search([('code', 'in', ('FR', 'GP', 'MQ', 'GF', 'RE', 'YT'))])
            if rec.country_id and rec.country_id in fr_countries and rec.zip and len(rec.zip) == 5:
                code = rec.zip[0:2]
                if code == '97':
                    code = rec.zip[0:3]
                department = self.env['res.country.department'].search([('code', '=', code),
                                                                        ('country_id', 'in', fr_countries.ids)],
                                                                       limit=1)
                rec.state_id = department and department.state_id or False
