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


class IrConfigParameterAltares(models.TransientModel):
    _inherit = 'res.config.settings'

    user_id_altares = fields.Char("UserID Altares")
    user_password_altares = fields.Char("Password Altares")

    @api.model
    def get_values(self):
        res = super().get_values()

        res.update(
            user_id_altares=self.env['ir.config_parameter'].get_param('altares_api.user_id_altares'),
            user_password_altares=self.env['ir.config_parameter'].get_param('altares_api.user_password_altares')
        )

        return res

    @api.multi
    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param('altares_api.user_id_altares', self.user_id_altares)
        self.env['ir.config_parameter'].sudo().set_param(
            'altares_api.user_password_altares', self.user_password_altares)
