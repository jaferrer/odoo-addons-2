# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api


class ColissimoBaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    login_colissimo = fields.Char(string=u"Numéro client",
                                  help=u"Utilisé pour la génération des étiquettes de suivi")
    password_colissimo = fields.Char(string=u"Mot de passe",
                                     help=u"Utilisé pour la génération des étiquettes de suivi")

    @api.multi
    def get_default_login_colissimo(self):
        login_colissimo = self.env['ir.config_parameter'].get_param(
            'generate_tracking_labels_colissimo.login_colissimo', default='')
        return {'login_colissimo': str(login_colissimo)}

    @api.multi
    def set_login_colissimo(self):
        config_parameters = self.env['ir.config_parameter']
        for record in self:
            config_parameters.set_param('generate_tracking_labels_colissimo.login_colissimo',
                                        record.login_colissimo or '')

    @api.multi
    def get_default_password_colissimo(self):
        password_colissimo = self.env['ir.config_parameter'].get_param(
            'generate_tracking_labels_colissimo.password_colissimo', default='')
        return {'password_colissimo': str(password_colissimo)}

    @api.multi
    def set_password_colissimo(self):
        config_parameters = self.env['ir.config_parameter']
        for record in self:
            config_parameters.set_param('generate_tracking_labels_colissimo.password_colissimo',
                                        record.password_colissimo or '')
