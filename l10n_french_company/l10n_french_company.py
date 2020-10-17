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
from odoo import fields, models, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    ape = fields.Char(related='partner_id.ape')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ape = fields.Char('APE')


class CompanyConfig(models.TransientModel):
    _name = 'company.config'
    _description = 'company.config'

    @api.model
    def update_lang(self, force_update=False):
        lang_fr = self.env['res.lang'].search([('code', '=', 'fr_FR')])
        if not lang_fr or force_update:
            self.env['base.language.install'].create({
                'lang': 'fr_FR',
                'overwrite': True
            }).lang_install()
        lang_fr.write({
            'date_format': "%d/%m/%Y",
            'grouping': '[3,3,3,3,3,3,3,3,3,3,3]',
            'decimal_point': ",",
            'thousands_sep': '&nbsp;',
            'time_format': "%H:%M",
            'active': True
        })
