# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import http
from odoo.http import request


class SSHController(http.Controller):

    @http.route("/ssh/<string:server_name>/<string:role_name>", type='http', auth='none', csrf=False)
    def ssh(self, server_name, role_name):
        server = request.env['ssh.server'].sudo().search([('name', '=', server_name)])
        if not server:
            return u""
        keys = server.allowed_keys_contents(role_name)
        if not keys:
            return u""
        return u"\n".join(keys) + u"\n"
