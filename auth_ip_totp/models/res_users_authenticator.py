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

import logging
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)
try:
    import pyotp
except ImportError:
    _logger.debug(
        'Could not import PyOTP. Please make sure this library is available in'
        ' your environment.'
    )


class ResUsersAuthenticator(models.Model):
    _name = 'res.users.authenticator'
    _description = 'MFA App/Device'
    _sql_constraints = [(
        'user_id_name_uniq',
        'UNIQUE(user_id, name)',
        _(
            'There is already an MFA app/device with this name associated with'
            ' your account. Please pick a new name and try again.'
        ),
    )]

    name = fields.Char(
        required=True,
        readonly=True,
    )
    secret_key = fields.Char(
        required=True,
        readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        ondelete='cascade',
    )

    @api.multi
    @api.constrains('user_id')
    def _check_has_user(self):
        self.filtered(lambda r: not r.user_id).unlink()

    @api.multi
    def validate_conf_code(self, confirmation_code):
        for record in self:
            totp = pyotp.TOTP(record.secret_key)
            if totp.verify(confirmation_code):
                return True

        return False
