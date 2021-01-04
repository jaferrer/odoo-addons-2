# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api


class purchase_delivery_tracking_chronopost_project_settings(models.TransientModel):
    _inherit = 'project.config.settings'

    token_chronopost = fields.Char(string="Token Suivi Chronopost")

    @api.multi
    def get_default_token_chronopost(self):
        token_chronopost = self.env['ir.config_parameter'].get_param("entrepot_project.token_chronopost", default='')
        return {'token_chronopost': token_chronopost}

    @api.multi
    def set_token_chronopost(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("entrepot_project.token_chronopost", record.token_chronopost or '')
