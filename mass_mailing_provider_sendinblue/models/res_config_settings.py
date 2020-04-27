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


class ResConfigSettingsSendinblue(models.TransientModel):
    _inherit = 'res.config.settings'

    sendinblue_api_key = fields.Char("Sendinblue API key", config_parameter='sendinblue_api_key')
    priorize_sendinblue_smtp = fields.Boolean("Sendinblue > Odoo (Mail templates)",
                                              config_parameter='priorize_sendinblue_smtp')
    priorize_sendinblue_contact = fields.Boolean("Sendinblue > Odoo (Contacts)",
                                                 config_parameter='priorize_sendinblue_contact')
    priorize_sendinblue_list = fields.Boolean("Sendinblue > Odoo (Lists)", config_parameter='priorize_sendinblue_list')
    priorize_sendinblue_campaign = fields.Boolean("Sendinblue > Odoo (Campaigns)",
                                                  config_parameter='priorize_sendinblue_campaign')
    priorize_sendinblue_folder = fields.Boolean("Sendinblue > Odoo (Folders)",
                                                config_parameter='priorize_sendinblue_folder')

    @api.model
    def get_values(self):
        res = super(ResConfigSettingsSendinblue, self).get_values()
        res.update(
            sendinblue_api_key=self.env['ir.config_parameter'].sudo().get_param('sendinblue_api_key'),
            priorize_sendinblue_smtp=self.env['ir.config_parameter'].sudo().get_param('priorize_sendinblue_smtp'),
            priorize_sendinblue_contact=self.env['ir.config_parameter'].sudo().get_param('priorize_sendinblue_contact'),
            priorize_sendinblue_list=self.env['ir.config_parameter'].sudo().get_param('priorize_sendinblue_list'),
            priorize_sendinblue_campaign=self.env['ir.config_parameter'].sudo().get_param(
                'priorize_sendinblue_campaign'),
            priorize_sendinblue_folder=self.env['ir.config_parameter'].sudo().get_param('priorize_sendinblue_folder'),
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettingsSendinblue, self).set_values()
        param = self.env['ir.config_parameter'].sudo()
        sendinblue_api_key = self.sendinblue_api_key or False
        param.set_param('sendinblue_api_key', sendinblue_api_key)

        priorize_sendinblue_smtp = self.priorize_sendinblue_smtp or False
        param.set_param('priorize_sendinblue_smtp', priorize_sendinblue_smtp)
        priorize_sendinblue_contact = self.priorize_sendinblue_contact or False
        param.set_param('priorize_sendinblue_contact', priorize_sendinblue_contact)
        priorize_sendinblue_list = self.priorize_sendinblue_list or False
        param.set_param('priorize_sendinblue_list', priorize_sendinblue_list)
        priorize_sendinblue_campaign = self.priorize_sendinblue_campaign or False
        param.set_param('priorize_sendinblue_campaign', priorize_sendinblue_campaign)
        priorize_sendinblue_folder = self.priorize_sendinblue_folder or False
        param.set_param('priorize_sendinblue_folder', priorize_sendinblue_folder)
