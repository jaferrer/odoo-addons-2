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

from openerp import fields, models, api, exceptions
from openerp.tools.safe_eval import safe_eval
from openerp.addons.connector.exception import FailedJobError

_logger = logging.getLogger(__name__)


class BusSendMessage(models.AbstractModel):
    _name = 'bus.send.message'

    url = fields.Char(u"Url")
    port = fields.Char(u"Port")
    database = fields.Char(u"Database")
    login = fields.Char(u"Login")
    password = fields.Char(u"Password")
    connection_status = fields.Char(string=u"Connection status", compute="get_connexion")

    @api.multi
    def get_connexion(self):
        for rec in self:
            server, res, connection = rec.try_connexion()
            rec.connection_status = res

    @api.multi
    def try_connexion(self, raise_error=False):
        self.ensure_one()
        url = "http://%s:%s/jsonrpc" % (self.recipient_subscriber_id.url, self.recipient_subscriber_id.port)
        server = jsonrpclib.Server(url)
        connection = False
        result = 0
        try:
            args = [
                self.recipient_subscriber_id.database,
                self.recipient_subscriber_id.login,
                self.recipient_subscriber_id.password
            ]
            connection = server.call(service="common", method="login", args=args)
            result = u"Error Login/Password" if connection == 0 else u"OK"
        except socket.error as e:
            result = e.strerror
        except jsonrpclib.ProtocolError:
            result = self._return_last_jsonrpclib_error()
        if raise_error and result != "OK":
            raise FailedJobError(result)
        return (server, result, connection)

    @api.multi
    def send_odoo_message(self, model, function, code, message):
        server, result, login = self.try_connexion(raise_error=True)
        args = [
            self.recipient_subscriber_id.database,
            login,
            self.recipient_subscriber_id.password,
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