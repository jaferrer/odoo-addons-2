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

from odoo import models, fields, api


class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    def _default_google_contacts_client_id(self):
        google_contacts_client_id = self.env['ir.config_parameter'].get_param('google_contacts_client_id')
        return google_contacts_client_id

    def _default_google_contacts_client_secret(self):
        google_contacts_client_secret = self.env['ir.config_parameter'].get_param('google_contacts_client_secret')
        return google_contacts_client_secret

    google_contacts_client_id = fields.Char(string="Client ID", default=_default_google_contacts_client_id)
    google_contacts_client_secret = fields.Char(string="Client Secret", default=_default_google_contacts_client_secret)

    @api.model
    def set_google_contacts_client_id(self):
        ir_config_param = self.env['ir.config_parameter']
        client_id = self.google_contacts_client_id
        ir_config_param.set_param('google_contacts_client_id', client_id, groups=['base.group_system'])

    @api.model
    def set_google_contacts_client_secret(self):
        ir_config_param = self.env['ir.config_parameter']
        client_secret = self.google_contacts_client_secret
        ir_config_param.set_param('google_contacts_client_secret', client_secret, groups=['base.group_system'])
