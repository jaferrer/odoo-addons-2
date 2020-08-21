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
# pylint: disable=broad-except
import base64
import logging
import psycopg2


from odoo import models, fields, api, tools, _
from odoo.addons.base.ir.ir_mail_server import MailDeliveryException
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class MailComposeMessageCcAndBcc(models.TransientModel):
    _inherit = 'mail.compose.message'

    partner_cc_ids = fields.Many2many('res.partner',
                                      'mail_compose_message_res_partner_cc_rel',
                                      'wizard_id',
                                      'partner_cc_id',
                                      string="Cc")
    partner_bcc_ids = fields.Many2many('res.partner',
                                       'mail_compose_message_res_partner_bcc_rel',
                                       'wizard_id',
                                       'partner_bcc_id',
                                       string="Bcc")

    @api.multi
    def send_mail_action(self):
        return super(MailComposeMessageCcAndBcc, self.with_context(cc_and_bcc=True)).send_mail_action()

    @api.multi
    def get_mail_values(self, res_ids):
        """
        Permet de passer le Cc et le Cci du 'mail.compose.message' vers le 'mail.message'.
        """
        res = super(MailComposeMessageCcAndBcc, self).get_mail_values(res_ids)

        if self.env.context.get('cc_and_bcc'):
            for res_id in res_ids:
                res[res_id].update({
                    'partner_cc_ids': [(6, 0, self.partner_cc_ids.ids)],
                    'partner_bcc_ids': [(6, 0, self.partner_bcc_ids.ids)],
                })

        return res


class MailmessageCcAndBcc(models.Model):
    _inherit = 'mail.message'

    partner_cc_ids = fields.Many2many('res.partner',
                                      'mail_message_res_partner_cc_rel',
                                      'mail_message_id',
                                      'partner_cc_id',
                                      string="Cc")
    partner_bcc_ids = fields.Many2many('res.partner',
                                       'mail_message_res_partner_bcc_rel',
                                       'mail_message_id',
                                       'partner_bcc_id',
                                       string="Bcc")


class MailmailCcAndBcc(models.Model):
    _inherit = 'mail.mail'

    email_bcc = fields.Char('Bcc', help='Blind carbon copy message recipients')

    @api.multi
    def send(self, auto_commit=False, raise_exception=False):
        """
        We need to rewrite the whole function just to add email_bcc argument to build_email() function.
        """
        ir_mail_server = self.env['ir.mail_server']

        for mail_id in self.ids:
            try:
                mail = self.browse(mail_id)
                # TDE note: remove me when model_id field is present on mail.message -
                # done here to avoid doing it multiple times in the sub method
                if mail.model:
                    model = self.env['ir.model'].sudo().search([('model', '=', mail.model)])[0]
                else:
                    model = None
                if model:
                    mail = mail.with_context(model_name=model.name)

                # load attachment binary data with a separate read(), as prefetching all
                # `datas` (binary field) could bloat the browse cache, triggerring
                # soft/hard mem limits with temporary data.
                attachments = [(a['datas_fname'], base64.b64decode(a['datas']))
                               for a in mail.attachment_ids.sudo().read(['datas_fname', 'datas'])]

                # specific behavior to customize the send email for notified partners
                email_list = []
                if mail.email_to:
                    email_list.append(mail.send_get_email_dict())
                for partner in mail.recipient_ids:
                    email_list.append(mail.send_get_email_dict(partner=partner))

                # headers
                headers = {}
                bounce_alias = self.env['ir.config_parameter'].get_param('mail.bounce.alias')
                catchall_domain = self.env['ir.config_parameter'].get_param('mail.catchall.domain')
                if bounce_alias and catchall_domain:
                    if mail.model and mail.res_id:
                        headers['Return-Path'] = '%s+%d-%s-%d@%s' % (
                            bounce_alias, mail.id, mail.model, mail.res_id, catchall_domain)
                    else:
                        headers['Return-Path'] = '%s+%d@%s' % (bounce_alias, mail.id, catchall_domain)
                if mail.headers:
                    try:
                        headers.update(safe_eval(mail.headers))
                    except Exception:
                        pass

                # Writing on the mail object may fail (e.g. lock on user) which
                # would trigger a rollback *after* actually sending the email.
                # To avoid sending twice the same email, provoke the failure earlier
                mail.write({
                    'state': 'exception',
                    'failure_reason': _(
                        "Error without exception. Probably due do sending an email without computed recipients."),
                })
                mail_sent = False

                # Update notification in a transient exception state to avoid concurrent
                # update in case an email bounces while sending all emails related to current
                # mail record.
                notifs = self.env['mail.notification'].search([
                    ('is_email', '=', True),
                    ('mail_message_id', 'in', mail.mapped('mail_message_id').ids),
                    ('res_partner_id', 'in', mail.mapped('recipient_ids').ids),
                    ('email_status', 'not in', ('sent', 'canceled'))
                ])
                if notifs:
                    notifs.sudo().write({
                        'email_status': 'exception',
                    })

                # build an RFC2822 email.message.Message object and send it without queuing
                res = None
                for email in email_list:
                    msg = ir_mail_server.build_email(
                        email_from=mail.email_from,
                        email_to=email.get('email_to'),
                        subject=mail.subject,
                        body=email.get('body'),
                        body_alternative=email.get('body_alternative'),
                        email_cc=tools.email_split(mail.email_cc),
                        email_bcc=tools.email_split(mail.email_bcc),
                        reply_to=mail.reply_to,
                        attachments=attachments,
                        message_id=mail.message_id,
                        references=mail.references,
                        object_id=mail.res_id and ('%s-%s' % (mail.res_id, mail.model)),
                        subtype='html',
                        subtype_alternative='plain',
                        headers=headers)
                    try:
                        res = ir_mail_server.send_email(msg, mail_server_id=mail.mail_server_id.id)
                    except AssertionError as error:
                        if error.message == ir_mail_server.NO_VALID_RECIPIENT:
                            # No valid recipient found for this particular
                            # mail item -> ignore error to avoid blocking
                            # delivery to next recipients, if any. If this is
                            # the only recipient, the mail will show as failed.
                            _logger.info("Ignoring invalid recipients for mail.mail %s: %s",
                                         mail.message_id, email.get('email_to'))
                        else:
                            raise
                if res:
                    mail.write({'state': 'sent', 'message_id': res, 'failure_reason': False})
                    mail_sent = True

                # /!\ can't use mail.state here, as mail.refresh() will cause an error
                # see revid:odo@openerp.com-20120622152536-42b2s28lvdv3odyr in 6.1
                if mail_sent:
                    _logger.info('Mail with ID %r and Message-Id %r successfully sent', mail.id, mail.message_id)
                mail._postprocess_sent_message(mail_sent=mail_sent)
            except MemoryError:
                # prevent catching transient MemoryErrors, bubble up to notify user or abort cron job
                # instead of marking the mail as failed
                _logger.exception("MemoryError while processing mail with ID %r and Msg-Id %r. Consider raising the "
                                  "--limit-memory-hard startup option", mail.id, mail.message_id)
                raise
            except psycopg2.Error:
                # If an error with the database occurs, chances are that the cursor is unusable.
                # This will lead to an `psycopg2.InternalError` being raised when trying to write
                # `state`, shadowing the original exception and forbid a retry on concurrent
                # update. Let's bubble it.
                raise
            except Exception as e:
                failure_reason = tools.ustr(e)
                _logger.exception("failed sending mail (id: %s) due to %s", mail.id, failure_reason)
                mail.write({'state': 'exception', 'failure_reason': failure_reason})
                mail._postprocess_sent_message(mail_sent=False)
                if raise_exception:
                    if isinstance(e, AssertionError):
                        # get the args of the original error, wrap into a value and throw a MailDeliveryException
                        # that is an except_orm, with name and value as arguments
                        value = '. '.join(e.args)
                        raise MailDeliveryException(_("Mail Delivery Failed"), value)
                    raise

            if auto_commit is True:
                self._cr.commit()
        return True


class ResPartnerCcAndBcc(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _notify_prepare_email_values(self, message):
        """
        Permet de passer le Cc et le Cci du 'mail.message' vers le 'mail.mail'.
        """
        res = super(ResPartnerCcAndBcc, self)._notify_prepare_email_values(message)

        email_cc_list = [partner.email for partner in message.partner_cc_ids]
        email_bcc_list = [partner.email for partner in message.partner_bcc_ids]
        email_cc = ",".join(email_cc_list)
        email_bcc = ",".join(email_bcc_list)
        res.update({
            'email_cc': email_cc,
            'email_bcc': email_bcc,
        })

        return res
