# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api, _


class MailAllowedRecipient(models.Model):
    _name = 'mail.allowed.recipient'

    partner_id = fields.Many2one('res.partner', string=u"Allowed recipient", required=True)
    email = fields.Char(string=u"Email", related='partner_id.email', readonly=True)


class AllowedRecipientMailMail(models.Model):
    _inherit = 'mail.mail'

    @api.multi
    def send(self, auto_commit=False, raise_exception=False):
        allowed_recipients = self.env['mail.allowed.recipient'].search([])
        allowed_recipient_emails = [recipient.email for recipient in allowed_recipients if recipient.email]
        mails_to_send = self
        if allowed_recipient_emails:
            for mail in self:
                message_vals_dict = []
                if mail.email_to:
                    message_vals_dict.append(mail.send_get_email_dict())
                for partner in mail.recipient_ids:
                    message_vals_dict.append(mail.send_get_email_dict(partner=partner))
                for values in message_vals_dict:
                    for recipient_email in values.get('email_to', []):
                        for allowed_email in allowed_recipient_emails:
                            if allowed_email not in recipient_email:
                                mails_to_send -= mail
                                mail.write({'state': 'exception',
                                            'failure_reason': _(u"%s is not in the list of allowed recipients.") %
                                                              recipient_email})
        return super(AllowedRecipientMailMail, mails_to_send).send(auto_commit=auto_commit,
                                                                   raise_exception=raise_exception)
