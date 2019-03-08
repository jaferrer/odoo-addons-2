# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import socket


import jsonrpclib

from openerp import models, fields, api
from openerp.addons.connector.exception import FailedJobError
from .. import jobs


class BackendHomeCron(models.Model):
    _inherit = 'ir.cron'

    bus_id = fields.Many2one('busextend.backend.batch', string=u"bus_batch")


class BackendPartner(models.Model):
    _inherit = 'res.partner'

    identifiant_bus = fields.Char('Identifiant BUS')


class Traitement(models.Model):
    _name = 'traitement.type'

    name = fields.Char(string=u'Name', required=True, index=True)
    description = fields.Text(string=u'Description')
    model_param_name = fields.Char(string=u'Model Name')
    method_name = fields.Char(string=u'Method Name')


class Busextendbackend(models.Model):
    _name = 'busextend.backend'
    _inherit = 'connector.backend'
    _backend_type = 'BUSEXTEND'

    name = fields.Char(string='name')
    version = fields.Selection([('v1', 'V1')], 'Version', default="v1")

    connexion_url = fields.Char(string='URL')
    user_id = fields.Many2one('res.users', string=u"User", inverse="_set_bus_information")
    port = fields.Integer(string='port')
    login = fields.Char(string='login')
    pwd = fields.Char(string='Mot de passe')
    db_odoo = fields.Char(string='Base de donnée')

    emetteur = fields.Many2one("res.partner", string="Emetteur")
    identifiant = fields.Char('Identifiant', related="emetteur.identifiant_bus", readonly=True)

    batch_ids = fields.One2many('busextend.backend.batch', 'backend_id', string=u"Fields")
    code_recep_response = fields.Char('code_recepteur_reponse')

    connexion_state = fields.Char(string="Etat de la connexion", compute='test_connexion', store=False)

    @api.multi
    def _set_bus_information(self):
        for rec in self:
            rec.login = rec.user_id.login
            rec.password = rec.user_id.password
            rec.connexion_url = rec.user_id.partner_id.website
            rec.port = rec.user_id.partner_id.zip
            rec.db_odoo = rec.user_id.partner_id.city

    @api.multi
    def test_connexion(self, context=None, raise_error=False):
        self.ensure_one()
        url = "http://%s:%s/jsonrpc" % (self.connexion_url, self.port)
        server = jsonrpclib.Server(url)
        # log in the given database

        result = 0

        try:
            result = server.call(service="common", method="login", args=[self.db_odoo, self.login, self.pwd])
            self.connexion_state = "Erreur Login/MdP" if result == 0 else "OK"
        except socket.error as e:
            self.connexion_state = e.strerror
        except jsonrpclib.ProtocolError:
            self.connexion_state = jobs._return_last_jsonrpclib_error()

        if raise_error and self.connexion_state != "OK":
            raise FailedJobError(self.connexion_state)

        return (server, result)
