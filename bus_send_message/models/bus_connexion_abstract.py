# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
#    along with this
#

import socket
import json
import jsonrpclib
import logging

from openerp import fields, models, api
from openerp.addons.connector.exception import FailedJobError

_logger = logging.getLogger(__name__)


class BusConnexionAbstract(models.AbstractModel):
    _name = 'bus.connexion.abstract'

    url = fields.Char(u"Url")
    port = fields.Char(u"Port")
    database = fields.Char(u"Database")
    login = fields.Char(u"Login")
    password = fields.Char(u"Password")
    # TODO: écrire un cron pour mettre à jour ce statut régulièrement
    connection_status = fields.Char(string=u"Connection status", readonly=True)

    @api.multi
    def try_connexion(self, raise_error=False):
        self.ensure_one()
        if self.port:
            url = "%s:%s/jsonrpc" % (self.url, self.port)
        else:
            url = "%s/jsonrpc" % self.url
        server = jsonrpclib.Server(url)
        connection = False
        try:
            args = [
                self.database,
                self.login,
                self.password
            ]
            _logger.info(u"Connectiong to URL %s, on database %s", url, self.database)
            connection = server.call(service="common", method="login", args=args)
            result = u"Error Login/Password" if connection == 0 else u"OK"
        except socket.error as e:
            result = e.strerror
        except jsonrpclib.ProtocolError:
            result = self._return_last_jsonrpclib_error()
        if raise_error and result != "OK":
            raise FailedJobError(result)
        if self.connection_status != result:
            self.connection_status = result
        return server, result, connection

    @api.multi
    def send_odoo_message(self, model, function, code, message):
        server, result, login = self.try_connexion(raise_error=True)
        args = [
            self.database,
            login,
            self.password,
            model,
            function,
            code,
            message
        ]
        try:
            result = server.call(service='object', method='execute', args=args)
            return result
        except jsonrpclib.ProtocolError:
            raise FailedJobError(self._return_last_jsonrpclib_error())

    def _return_last_jsonrpclib_error(self):
        return json.loads(jsonrpclib.history.response).get('error').get('data').get('message')
