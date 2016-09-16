# -*- coding: utf8 -*-
#
# Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import requests

from openerp import fields, models, api, exceptions


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def auth_oauth(self, provider, params):
        prov = self.env['auth.oauth.provider'].browse(provider).sudo()
        if prov.type != 'code':
            return super(ResUsers, self).auth_oauth(provider, params)

        access_token = params.get('access_token')
        if not prov.data_endpoint:
            raise exceptions.AccessDenied()

        validation = self.sudo()._auth_oauth_rpc(prov.data_endpoint, params['access_token'])
        validation["user_id"] = validation["username"]

        # retrieve and sign in user
        login = self._auth_oauth_signin(provider, validation, params)
        if not login:
            raise exceptions.AccessDenied()
        # return user credentials
        return (self.env.cr.dbname, login, access_token)
