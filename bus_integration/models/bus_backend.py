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
from ..connector.jobs import _return_last_jsonrpclib_error


class Busextendbackend(models.Model):
    _name = 'bus.backend'
    _inherit = 'connector.backend'
    _backend_type = 'BUSEXTEND'

    name = fields.Char(u"Name")
    version = fields.Selection([('v1', 'V1')], u"Version", default='v1')
    connexion_url = fields.Char(u"URL")
    user_id = fields.Many2one('res.users', string=u"User", inverse="_set_bus_information")
    port = fields.Integer(u"Port")
    login = fields.Char(u"Login")
    password = fields.Char(u"Password")
    db_odoo = fields.Char(u"Odoo database")
    sender_id = fields.Many2one('res.partner', u"Sender")
    bus_username = fields.Char(u"BUS user name", related='sender_id.bus_username', readonly=True)
    batch_ids = fields.One2many('bus.backend.batch', 'backend_id', string=u"Fields")
    # TODO: autres types de réception à implémenter
    reception_treatment = fields.Selection([('simple_reception', u"Simple reception")],
                                           u"Message Reception Treatment", required=True)
    connexion_state = fields.Char(u"Connexion status", compute='test_connexion', store=False)
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
            result = server.call(service="common", method="login", args=[self.db_odoo, self.login, self.password])
            self.connexion_state = "Erreur Login/MdP" if result == 0 else "OK"
        except socket.error as e:
            self.connexion_state = e.strerror
        except jsonrpclib.ProtocolError:
            self.connexion_state = _return_last_jsonrpclib_error()
        if raise_error and self.connexion_state != "OK":
            raise FailedJobError(self.connexion_state)
        return (server, result)
