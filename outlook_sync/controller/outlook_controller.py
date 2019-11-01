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

from odoo import http, registry
from odoo.http import request


class OutlookController(http.Controller):

    @http.route('/outlook_odoo', type='http', auth='none')
    def get_authorization_code(self, **kwargs):
        """
        Permet de récupérer le code d'autorisation envoyé par Microsoft.
        """

        state = json.loads(kwargs['state'])
        dbname = state.get('d')
        user_id = state.get('user_id')
        scope = state.get('scope')

        with registry(dbname).cursor() as cr:
            if kwargs.get('code'):
                request.env(cr, request.session.uid)['outlook.sync.wizard'].get_refresh_token(
                    kwargs['code'], user_id, scope)
            elif kwargs.get('error'):
                return redirect("%s%s" % ("?error=", kwargs['error']))
            else:
                return redirect("%s" % ("?error=Unknown_error"))
