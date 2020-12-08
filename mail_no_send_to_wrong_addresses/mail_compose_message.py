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
from odoo import api, models, exceptions


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail_action(self):
        if not self.partner_ids:
            raise exceptions.ValidationError(u"No addressee informed !")
        partner_no_mail = [partner.display_name for partner in self.partner_ids if not partner.email]
        if partner_no_mail:
            raise exceptions.ValidationError(u"No email address for the recipient : %s"
                                             % u", ".join(partner_no_mail))
        return super(MailComposeMessage, self).send_mail_action()
