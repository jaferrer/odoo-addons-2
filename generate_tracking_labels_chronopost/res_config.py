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

    login_chronopost = fields.Char(string=u"Numéro de compte Chronopost",
                                  help=u"Utilisé pour la génération des étiquettes de suivi")
    password_chronopost = fields.Char(string=u"Mot de passe Chronopost",
                                     help=u"Utilisé pour la génération des étiquettes de suivi")
    pre_alert_chronopost = fields.Selection([('0', u"Pas de préalerte"),
                                             ('11', u"Abonnement tracking expéditeur")],
                                            string=u"Pré-alerte Chronopost pour les envois", default='0')

    @api.multi
    def get_default_login_chronopost(self):
        login_chronopost = self.env['ir.config_parameter'].get_param(
            'generate_tracking_labels_chronopost.login_chronopost', default='')
        return {'login_chronopost': str(login_chronopost)}

    @api.multi
    def set_login_chronopost(self):
        config_parameters = self.env['ir.config_parameter']
        for record in self:
            config_parameters.set_param('generate_tracking_labels_chronopost.login_chronopost',
                                        record.login_chronopost or '')

    @api.multi
    def get_default_password_chronopost(self):
        password_chronopost = self.env['ir.config_parameter'].get_param(
            'generate_tracking_labels_chronopost.password_chronopost', default='')
        return {'password_chronopost': str(password_chronopost)}

    @api.multi
    def set_password_chronopost(self):
        config_parameters = self.env['ir.config_parameter']
        for record in self:
            config_parameters.set_param('generate_tracking_labels_chronopost.password_chronopost',
                                        record.password_chronopost or '')

    @api.multi
    def get_default_pre_alert_chronopost(self):
        pre_alert_chronopost = self.env['ir.config_parameter'].get_param(
            'generate_tracking_labels_chronopost.pre_alert_chronopost', default='0')
        return {'pre_alert_chronopost': str(pre_alert_chronopost)}

    @api.multi
    def set_pre_alert_chronopost(self):
        config_parameters = self.env['ir.config_parameter']
        for record in self:
            config_parameters.set_param('generate_tracking_labels_chronopost.pre_alert_chronopost',
                                        record.pre_alert_chronopost or '0')
