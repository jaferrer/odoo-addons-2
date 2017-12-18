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

    login_mondial = fields.Char(string=u"Numéro de compte Mondial Relais",
                                help=u"Utilisé pour la génération des étiquettes de suivi")
    password_mondial = fields.Char(string=u"Mot de passe Mondial Relais",
                                   help=u"Utilisé pour la génération des étiquettes de suivi")

    societe_mondial = fields.Char(string=u"Société Mondial Relais",
                                help=u"Utilisé pour la génération des étiquettes de suivi")
    marque_mondial = fields.Char(string=u"Marque Mondial Relais",
                                help=u"Utilisé pour la génération des étiquettes de suivi")
    code_marque_mondial = fields.Char(string=u"Code marque Mondial Relais",
                                help=u"Utilisé pour la génération des étiquettes de suivi")
    origine_mondial = fields.Char(string=u"Origine Mondial Relais",
                                      help=u"Utilisé pour la génération des étiquettes de suivi")

    @api.multi
    def get_default_code_origine_mondial(self):
        origine_mondial = self.env['ir.config_parameter'].get_param(
            'generate_tracking_labels_mondial_relay.origine_mondial', default='')
        return {'origine_mondial': str(origine_mondial)}

    @api.multi
    def set_code_origine_mondial(self):
        config_parameters = self.env['ir.config_parameter']
        for record in self:
            config_parameters.set_param('generate_tracking_labels_mondial_relay.origine_mondial',
                                        record.origine_mondial or '')

    @api.multi
    def get_default_code_marque_mondial(self):
        code_marque_mondial = self.env['ir.config_parameter'].get_param(
            'generate_tracking_labels_mondial_relay.code_marque_mondial', default='')
        return {'code_marque_mondial': str(code_marque_mondial)}

    @api.multi
    def set_code_marque_mondial(self):
        config_parameters = self.env['ir.config_parameter']
        for record in self:
            config_parameters.set_param('generate_tracking_labels_mondial_relay.code_marque_mondial',
                                        record.code_marque_mondial or '')

    @api.multi
    def get_default_marque_mondial(self):
        marque_mondial = self.env['ir.config_parameter'].get_param(
            'generate_tracking_labels_mondial_relay.marque_mondial', default='')
        return {'marque_mondial': str(marque_mondial)}

    @api.multi
    def set_marque_mondial(self):
        config_parameters = self.env['ir.config_parameter']
        for record in self:
            config_parameters.set_param('generate_tracking_labels_mondial_relay.marque_mondial',
                                        record.marque_mondial or '')

    @api.multi
    def get_default_societe_mondial(self):
        societe_mondial = self.env['ir.config_parameter'].get_param(
            'generate_tracking_labels_mondial_relay.societe_mondial', default='')
        return {'societe_mondial': str(societe_mondial)}

    @api.multi
    def set_societe_mondial(self):
        config_parameters = self.env['ir.config_parameter']
        for record in self:
            config_parameters.set_param('generate_tracking_labels_mondial_relay.societe_mondial',
                                        record.societe_mondial or '')

    @api.multi
    def get_default_login_chronopost(self):
        login_mondial = self.env['ir.config_parameter'].get_param(
            'generate_tracking_labels_mondial_relay.login_mondial', default='')
        return {'login_mondial': str(login_mondial)}

    @api.multi
    def set_login_chronopost(self):
        config_parameters = self.env['ir.config_parameter']
        for record in self:
            config_parameters.set_param('generate_tracking_labels_mondial_relay.login_mondial',
                                        record.login_mondial or '')

    @api.multi
    def get_default_password_chronopost(self):
        password_mondial = self.env['ir.config_parameter'].get_param(
            'generate_tracking_labels_mondial_relay.password_mondial', default='')
        return {'password_mondial': str(password_mondial)}

    @api.multi
    def set_password_chronopost(self):
        config_parameters = self.env['ir.config_parameter']
        for record in self:
            config_parameters.set_param('generate_tracking_labels_mondial_relay.password_mondial',
                                        record.password_mondial or '')
