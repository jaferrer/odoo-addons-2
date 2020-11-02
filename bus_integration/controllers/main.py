# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
import logging
from urlparse import urlparse
from openerp import http, _
from openerp.http import request
from openerp.addons.web.controllers.main import Home

_logger = logging.getLogger(__name__)


class HomeController(Home):

    @staticmethod
    def _is_an_ip(hostname):
        try:
            socket.inet_aton(hostname)
            return True
        except socket.error:
            return False

    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        """
          Makes sure web.base.url is a domain is set with a domain name not an IP address To avoid bus synchronisation
          locks. Raise an error if not OK
        """
        base_url = request.httprequest.base_url
        hostname = urlparse(base_url).hostname
        local_env = hostname == '127.0.0.1'  # do not bother developers
        if not local_env and HomeController._is_an_ip(hostname):
            values = request.params.copy()
            values['error'] = _("Please log in using a domain name not an IP address")
            return request.render('web.login', values)

        return super(HomeController, self).web_login(redirect, **kw)
