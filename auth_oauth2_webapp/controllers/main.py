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

import json
import werkzeug
import logging
import requests

from openerp import http, api, exceptions

from openerp.http import request
from openerp.addons.web.controllers.main import set_cookie_and_redirect, login_and_redirect
from openerp.addons.auth_oauth.controllers.main import OAuthLogin, OAuthController, fragment_to_query_string
from openerp.modules.registry import RegistryManager

_logger = logging.getLogger(__name__)


class OAuthLoginWebApp(OAuthLogin):
    def list_providers(self):
        try:
            provider_obj = request.env['auth.oauth.provider'].sudo()
            providers = provider_obj.search_read([('enabled', '=', True)])
        except Exception:
            providers = []
        for provider in providers:
            return_url = request.httprequest.url_root + 'auth_oauth/signin'
            state = self.get_state(provider)
            params = dict(
                response_type=provider['type'],
                client_id=provider['client_id'],
                redirect_uri=return_url,
                scope=provider['scope'],
                state=json.dumps(state),
            )
            provider['auth_link'] = provider['auth_endpoint'] + '?' + werkzeug.url_encode(params)

        return providers


class OAuthControllerWebApp(OAuthController):
    @http.route()
    @fragment_to_query_string
    def signin(self, **kw):
        if not kw['code']:
            # we are not in the WebApp (code) OAuth2 protocol
            return super(OAuthControllerWebApp, self).signin(self, kw)

        # First get the access_token from the server
        state = json.loads(kw['state'])
        provider_id = state['p']
        provider = request.env['auth.oauth.provider'].sudo().browse(provider_id)
        post_data = {
            'grant_type': 'authorization_code',
            'code': kw['code'],
            'redirect_uri': request.httprequest.url_root + 'auth_oauth/signin',
            'client_id': provider.client_id,
            'client_secret': provider.client_secret
        }
        resp = requests.post(provider.validation_endpoint, json=post_data)
        resp.raise_for_status()
        data = resp.json()
        if 'error' in data:
            _logger.exception("OAuth2: %s" % data['error'])
            url = "/web/login?oauth_error=2"
            return set_cookie_and_redirect(url)

        # Then continue with our authentication
        with api.Environment.manage():
            dbname = state['d']
            registry = RegistryManager.get(dbname)
            with registry.cursor() as cr:
                new_env = api.Environment(cr, request.env.uid, request.env.context)
                try:
                    redirect = werkzeug.url_unquote_plus(state['r']) if state.get('r') else False
                    kw.update({'access_token': data['access_token']})
                    credentials = new_env['res.users'].sudo().auth_oauth(provider.id, kw)
                    new_env.cr.commit()
                    action = state.get('a')
                    menu = state.get('m')
                    url = '/web'
                    if redirect:
                        url = redirect
                    elif action:
                        url = '/web#action=%s' % action
                    elif menu:
                        url = '/web#menu_id=%s' % menu
                    return login_and_redirect(*credentials, redirect_url=url)
                except AttributeError:
                    # auth_signup is not installed
                    _logger.error("auth_signup not installed on database %s: oauth sign up cancelled." % (dbname,))
                    url = "/web/login?oauth_error=1"
                except exceptions.AccessDenied:
                    # oauth credentials not valid, user could be on a temporary session
                    _logger.info('OAuth2: access denied, redirect to main page in case a valid session exists, '
                                 'without setting cookies')
                    url = "/web/login?oauth_error=3"
                    redirect = werkzeug.utils.redirect(url, 303)
                    redirect.autocorrect_location_header = False
                    return redirect
                except Exception, e:
                    # signup error
                    _logger.exception("OAuth2: %s" % str(e))
                    url = "/web/login?oauth_error=2"

        return set_cookie_and_redirect(url)
