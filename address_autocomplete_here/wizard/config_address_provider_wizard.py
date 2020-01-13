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

from odoo import fields, models, api


class ConfigHerculePro(models.TransientModel):
    _inherit = 'base.config.settings'

    url_address_provider = fields.Char(u"URL Here")
    apikey_address_provider = fields.Char(u"Clef API")
    country_address_provider = fields.Char(u"Pays")

    @api.multi
    def get_default_url_address_provider(self, fields):
        return {'url_address_provider': self.env['ir.config_parameter'].get_param('url_address_provider')}

    @api.multi
    def set_default_url_address_provider(self):
        for rec in self:
            value = rec.url_address_provider
            self.env['ir.config_parameter'].set_param('url_address_provider', value)

    @api.multi
    def get_default_apikey_address_provider(self, fields):
        return {'apikey_address_provider': self.env['ir.config_parameter'].get_param('apikey_address_provider')}

    @api.multi
    def set_default_apikey_address_provider(self):
        for rec in self:
            value = rec.apikey_address_provider
            self.env['ir.config_parameter'].set_param('apikey_address_provider', value)

    @api.multi
    def get_default_country_address_provider(self, fields):
        return {'country_address_provider': self.env['ir.config_parameter'].get_param('country_address_provider')}

    @api.multi
    def set_default_country_address_provider(self):
        for rec in self:
            value = rec.country_address_provider
            self.env['ir.config_parameter'].set_param('country_address_provider', value)
