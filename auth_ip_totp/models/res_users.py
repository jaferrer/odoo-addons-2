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

from collections import defaultdict
from uuid import uuid4
from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError, AccessDenied
from odoo.http import request
from ..controllers.main import JsonSecureCookie
from ..exceptions import MfaLoginNeeded


class ResUsers(models.Model):
    _inherit = 'res.users'
    _mfa_uid_cache = defaultdict(set)

    @classmethod
    def _build_model(cls, pool, cr):
        model_cls = super(ResUsers, cls)._build_model(pool, cr)
        model_cls.SELF_WRITEABLE_FIELDS += ['mfa_enabled', 'authenticator_ids']
        return model_cls

    mfa_authorized = fields.Boolean(u"MFA authorized",
                                    help=u"When checked, the user will be allowed to setup MFA and "
                                         u"thus access Odoo while roaming.")
    mfa_enabled = fields.Boolean(string=u"MFA Enabled")
    authenticator_ids = fields.One2many(
        comodel_name='res.users.authenticator',
        inverse_name='user_id',
        string=u"Authentication Apps/Devices",
        help=u"To delete an authentication app, remove it from this list. To"
             u" add a new authentication app, please use the button to the"
             u" right. If the button is not present, you do not have the"
             u" permissions to do this.",
    )
    trusted_device_cookie_key = fields.Char(
        compute='_compute_trusted_device_cookie_key',
        store=True,
    )

    @api.multi
    @api.depends('mfa_enabled')
    def _compute_trusted_device_cookie_key(self):
        for record in self:
            if record.mfa_enabled:
                record.trusted_device_cookie_key = uuid4()
            else:
                record.trusted_device_cookie_key = False

    @api.multi
    @api.constrains('mfa_enabled', 'authenticator_ids')
    def _check_enabled_with_authenticator(self):
        for record in self:
            if record.mfa_enabled and not record.authenticator_ids:
                raise ValidationError(_(
                    'You have MFA enabled but do not have any authentication'
                    ' apps/devices set up. To keep from being locked out,'
                    ' please add one before you activate this feature.'
                ))

    @api.multi
    @api.constrains('mfa_enabled', 'mfa_authorized')
    def _check_mfa_authorized(self):
        for rec in self:
            if rec.mfa_enabled and not rec.mfa_authorized:
                raise ValidationError(_(u"You are not authorized to setup MFA."))

    @api.model
    def create(self, values):
        if 'mfa_authorized' in values and not values['mfa_authorized']:
            values['mfa_enabled'] = False
        return super(ResUsers, self).create(values)

    @api.multi
    def write(self, values):
        if 'mfa_authorized' in values and not values['mfa_authorized']:
            values['mfa_enabled'] = False
        return super(ResUsers, self).write(values)

    @classmethod
    def check(cls, db, uid, password):
        """Prevent auth caching for MFA users without active MFA session"""
        if uid in cls._mfa_uid_cache[db]:
            if not request or request.session.get('mfa_login_active') != uid:
                cls._Users__uid_cache[db].pop(uid, None)

        return super(ResUsers, cls).check(db, uid, password)

    @api.model
    def check_credentials(self, password):
        """Add MFA logic to core authentication process.

        Overview:
            * If request comes from authorized IP, defer to parent logic.
            * If we are SUPERUSER and no authorized IPs have been set, defer to parent logic
            to prevent lock-out.
            * From here, deny access to all users that are not allowed to setup MFA.
            * If user has MFA enabled and has gone through MFA login process
              this session or has correct device cookie, defer to parent logic.
            * If neither of these is true, call parent logic. If successful,
              prevent auth while updating session to indicate that MFA login
              process can now commence.
        """
        if request and self.env['authorized.ip'].check_ip(request.httprequest.remote_addr):
            return super(ResUsers, self).check_credentials(password)

        if self.env.uid == tools.SUPERUSER_ID and not self.env['authorized.ip'].ips_defined():
            # Anti-lockout rule: if no ips are defined, superuser can login directly.
            return super(ResUsers, self).check_credentials(password)

        if not self.env.user.mfa_enabled:
            raise AccessDenied()

        self._mfa_uid_cache[self.env.cr.dbname].add(self.env.uid)

        if request:
            if request.session.get('mfa_login_active') == self.env.uid:
                return super(ResUsers, self).check_credentials(password)

            cookie_key = 'trusted_devices_%d' % self.env.uid
            device_cook = request.httprequest.cookies.get(cookie_key)
            if device_cook:
                secret = self.env.user.trusted_device_cookie_key
                device_cook = JsonSecureCookie.unserialize(device_cook, secret)
                if device_cook:
                    return super(ResUsers, self).check_credentials(password)

        super(ResUsers, self).check_credentials(password)
        if request:
            request.session['mfa_login_needed'] = True
        raise MfaLoginNeeded

    @api.multi
    def validate_mfa_confirmation_code(self, confirmation_code):
        self.ensure_one()
        return self.authenticator_ids.validate_conf_code(confirmation_code)
