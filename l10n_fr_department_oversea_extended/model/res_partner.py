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

from odoo import models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends('zip', 'country_id', 'country_id.code')
    # If a department code changes, it will have to be manually recomputed
    def _compute_department(self):
        oversea_list = ('FR', 'GP', 'MQ', 'GF', 'RE', 'YT', 'PM', 'BL', 'MF', 'WF', 'PF', 'NC', 'TF')
        rcdo = self.env['res.country.department']
        fr_country_ids = self.env['res.country'].search([
            ('code', 'in', oversea_list)]).ids
        for partner in self:
            dpt_id = False
            zipcode = partner.zip
            if (
                    partner.country_id and
                    partner.country_id.id in fr_country_ids and
                    zipcode and
                    len(zipcode) == 5):
                zipcode = partner.zip.strip().replace(' ', '').rjust(5, '0')
                code = zipcode[0:2]
                if code in ('97', '98'):
                    code = zipcode[0:3]
                if code == '20':
                    code = self._compute_department_corsica(zipcode)
                dpts = rcdo.search([
                    ('code', '=', code),
                    ('country_id', 'in', fr_country_ids),
                ])
                if len(dpts) == 1:
                    dpt_id = dpts[0].id
            partner.department_id = dpt_id
