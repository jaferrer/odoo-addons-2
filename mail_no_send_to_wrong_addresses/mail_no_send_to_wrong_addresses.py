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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import re

from odoo import models, api


class MailMessageNoSenf(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def is_email_address_ok(self):
        self.ensure_one()
        if self.email:
            match = re.match(r'^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', self.email)
            if not match:
                return False
        return True

    @api.multi
    def _notify(self, message, force_send=False, send_after_commit=True, user_signature=True):
        partners_to_notify = self.env['res.partner']
        for rec in self:
            if not rec.email or not rec.is_email_address_ok():
                continue
            partners_to_notify |= rec
        return super(MailMessageNoSenf, partners_to_notify)._notify(message, force_send=force_send,
                                                                    send_after_commit=send_after_commit,
                                                                    user_signature=user_signature)
