# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from datetime import datetime, timedelta
import base64
import json
from werkzeug.contrib.securecookie import SecureCookie, UnquoteError
from werkzeug.contrib.sessions import ModificationTrackingDict
from werkzeug._compat import to_bytes
from werkzeug.wrappers import Response as WerkzeugResponse
from odoo import _, http
from odoo.http import Response, request
from odoo.addons.web.controllers.main import Home


class JsonSecureCookie(SecureCookie):
    serialization_method = json

    # Monkey patch 1:
    # see: https://github.com/pallets/werkzeug/commit/
    #      576b75d85e97fc23441e766a9714edc6993bde25

    def __init__(self, data=None, secret_key=None, new=True):
        ModificationTrackingDict.__init__(self, data or ())
        # explicitly convert it into a bytestring because python 2.6
        # no longer performs an implicit string conversion on hmac
        if secret_key is not None:
            secret_key = to_bytes(secret_key, 'utf-8')
        self.secret_key = secret_key
        self.new = new

    # Monkey patch 2:
    # see: https://github.com/pallets/werkzeug/issues/953

    @classmethod
    def quote(cls, value):
        if cls.serialization_method is not None:
            value = cls.serialization_method.dumps(value)
            value = value.encode('utf-8')
        if cls.quote_base64:
            value = b''.join(base64.b64encode(value).splitlines()).strip()
        return value

    @classmethod
    def unquote(cls, value):
        try:
            if cls.quote_base64:
                value = base64.b64decode(value)
            value = str(value)
            if cls.serialization_method is not None:
                value = cls.serialization_method.loads(value)
            return value
        except Exception:
            raise UnquoteError()


class AuthTotp(Home):
    @http.route()
    def web_login(self, *args, **kwargs):
        response = super(AuthTotp, self).web_login(*args, **kwargs)

        if request.session.get('mfa_login_needed'):
            request.session['mfa_login_needed'] = False
            return http.local_redirect(
                '/auth_totp/login',
                query={'redirect': request.params.get('redirect')},
                keep_hash=True,
            )

        return response

    @http.route(
        '/auth_totp/login',
        type='http',
        auth='public',
        methods=['GET'],
        website=True,
    )
    def mfa_login_get(self, *args, **kwargs):
        return request.render('auth_ip_totp.mfa_login', qcontext=request.params)

    @http.route('/auth_totp/login', type='http', auth='none', methods=['POST'])
    def mfa_login_post(self, *args, **kwargs):
        """Process MFA login attempt.

        Overview:
            * Identify current user based on login in session. If this doesn't
              work, redirect to the password login page with an error message.
            * Validate the confirmation code provided by the user. If it's not
              valid, redirect to the previous login step with an error message.
            * Update the session to indicate that the MFA login process for
              this user is complete and attempt password authentication again.
            * Build a trusted device cookie and add it to the response if the
              trusted device option was checked.
            * Redirect to the provided URL or to '/web' if one was not given.
        """

        # sudo() is required because there is no request.env.uid (likely since
        # there is no user logged in at the start of the request)
        user_model_sudo = request.env['res.users'].sudo()
        config_model_sudo = user_model_sudo.env['ir.config_parameter'].sudo()

        user_login = request.session.get('login')
        user = user_model_sudo.search([('login', '=', user_login)])
        if not user:
            return http.local_redirect(
                '/web/login',
                query={
                    'redirect': request.params.get('redirect'),
                    'error': _(
                        'You must log in with a password before starting the'
                        ' MFA login process.'
                    ),
                },
                keep_hash=True,
            )

        confirmation_code = request.params.get('confirmation_code')
        if not user.validate_mfa_confirmation_code(confirmation_code):
            return http.local_redirect(
                '/auth_totp/login',
                query={
                    'redirect': request.params.get('redirect'),
                    'error': _(
                        'Your confirmation code is not correct. Please try'
                        ' again.'
                    ),
                },
                keep_hash=True,
            )
        request.session['mfa_login_active'] = user.id

        user_pass = request.session.get('password')
        uid = request.session.authenticate(request.db, user.login, user_pass)
        if uid:
            request.params['login_success'] = True

        redirect = request.params.get('redirect')
        if not redirect:
            redirect = '/web'
        response = http.redirect_with_hash(redirect)
        if not isinstance(response, WerkzeugResponse):
            response = Response(response)

        if request.params.get('remember_device'):
            secret = user.trusted_device_cookie_key
            device_cookie = JsonSecureCookie({'user_id': user.id}, secret)
            cookie_lifetime = timedelta(days=30)
            cookie_exp = datetime.utcnow() + cookie_lifetime
            device_cookie = device_cookie.serialize(cookie_exp)
            cookie_key = 'trusted_devices_%d' % user.id
            sec_config = config_model_sudo.get_param('auth_ip_totp.secure_cookie')
            security_flag = sec_config != '0'
            response.set_cookie(
                cookie_key,
                device_cookie,
                max_age=cookie_lifetime.total_seconds(),
                expires=cookie_exp,
                httponly=True,
                secure=security_flag,
            )

        return response