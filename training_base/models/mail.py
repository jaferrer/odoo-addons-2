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

from odoo import models


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    def action_send_mail(self):
        if 'send_mail_convocation' in self.env.context:
            (partner_id, sitting_id) = self.env.context['send_mail_convocation']
            attachment = self.attachment_ids[0]
            attachment.write({'res_model': 'res.partner',
                              'res_id': partner_id})
            self.env['training.sitting.convocation.sent'].create_or_update_line(partner_id, sitting_id, attachment)
        if 'send_mail_certificate' in self.env.context:
            (partner_id, session_id) = self.env.context['send_mail_certificate']
            attachment = self.attachment_ids[0]
            attachment.write({'res_model': 'res.partner',
                              'res_id': partner_id})
            self.env['training.session.certificate.sent'].create_or_update_line(partner_id, session_id, attachment)
        return super(MailComposer, self).action_send_mail()
