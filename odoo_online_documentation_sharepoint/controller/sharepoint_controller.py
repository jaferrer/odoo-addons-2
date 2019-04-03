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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import json

from werkzeug.utils import redirect

from openerp import http, registry
from openerp.http import request


class SharepointController(http.Controller):

    @http.route('/sirail_sharepoint', type='http', auth='none')
    def get_authorization_code(self, **kwargs):
        """
        Allow to catch the authorization code form Microsoft.
        """

        state = json.loads(kwargs['state'])
        dbname = state.get('d')
        # service = state.get('s')
        # url_return = state.get('f')

        with registry(dbname).cursor() as cr:
            if kwargs.get('code'):
                request.env(cr, request.session.uid)['knowledge.config.settings'].get_refresh_token(kwargs['code'])
                # return redirect(url_return)
            elif kwargs.get('error'):
                # return redirect("%s%s%s" % (url_return, "?error=", kwargs['error']))
                return redirect("%s%s" % ("?error=", kwargs['error']))
            else:
                # return redirect("%s%s" % (url_return, "?error=Unknown_error"))
                return redirect("%s" % ("?error=Unknown_error"))
