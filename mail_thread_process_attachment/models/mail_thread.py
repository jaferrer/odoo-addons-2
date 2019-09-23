# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import email
import xmlrpclib
import logging

from odoo import models, api, tools

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.model
    def message_process(self, model, message, custom_values=None,
                        save_original=False, strip_attachments=False,
                        thread_id=None):
        """Overridden her to read email attachment if any.

        Process an incoming RFC2822 email message, relying on
        ``mail.message.parse()`` for the parsing operation,
        and ``message_route()`` to figure out the target model.

        Once the target model is known, its ``message_new`` method
        is called with the new message (if the thread record did not exist)
        or its ``message_update`` method (if it did).

        There is a special case where the target model is False: a reply
        to a private message. In this case, we skip the message_new /
        message_update step, to just post a new message using mail_thread
        message_post.

        :param string model: the fallback model to use if the message
           does not match any of the currently configured mail aliases
           (may be None if a matching alias is supposed to be present)
        :param message: source of the RFC2822 message
        :type message: string or xmlrpclib.Binary
        :type dict custom_values: optional dictionary of field values
            to pass to ``message_new`` if a new record needs to be created.
            Ignored if the thread record already exists, and also if a
            matching mail.alias was found (aliases define their own defaults)
        :param bool save_original: whether to keep a copy of the original
            email source attached to the message after it is imported.
        :param bool strip_attachments: whether to strip all attachments
            before processing the message, in order to save some space.
        :param int thread_id: optional ID of the record/thread from ``model``
           to which this mail should be attached. When provided, this
           overrides the automatic detection based on the message
           headers."""
        # extract message bytes - we are forced to pass the message as binary because
        # we don't know its encoding until we parse its headers and hence can't
        # convert it to utf-8 for transport between the mailgate script and here.
        if isinstance(message, xmlrpclib.Binary):
            message = str(message.data)
        # Warning: message_from_string doesn't always work correctly on unicode,
        # we must use utf-8 strings here :-(
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        msg_txt = email.message_from_string(message)

        # parse the message, verify we are not in a loop by checking message_id is not duplicated
        msg = self.message_parse(msg_txt, save_original=save_original)
        if strip_attachments:
            msg.pop('attachments', None)

        if msg.get('message_id'):   # should always be True as message_parse generate one if missing
            existing_msg_ids = self.env['mail.message'].search([('message_id', '=', msg.get('message_id'))])
            if existing_msg_ids:
                _logger.info(
                    'Ignored mail from %s to %s with Message-Id %s: found duplicated Message-Id during processing',
                    msg.get('from'), msg.get('to'), msg.get('message_id'))
                return False

        # find possible routes for the message
        routes = self.message_route(msg_txt, msg, model, thread_id, custom_values)
        # Handle messages embedded as attachment as the original message
        for att in msg.get('attachments', []):
            if att.info.get('message') and not self.env.context.get('message_extracted'):
                if isinstance(att.content, list):
                    embedded_msg = att.content[0]
                else:
                    embedded_msg = att.content
                return self.with_context(message_extracted=True).message_process(
                    routes[0][0], embedded_msg.as_string(), custom_values=routes[0][2], save_original=save_original,
                    strip_attachments=strip_attachments, thread_id=routes[0][1]
                )
        thread_id = self.message_route_process(msg_txt, msg, routes)
        return thread_id

    def _message_extract_payload(self, message, save_original=False):
        """Extract body as HTML and attachments from the mail message"""
        attachments = []
        body = u''
        if save_original:
            attachments.append(self._Attachment('original_email.eml', message.as_string(), {}))

        # Be careful, content-type may contain tricky content like in the
        # following example so test the MIME type with startswith()
        #
        # Content-Type: multipart/related;
        #   boundary="_004_3f1e4da175f349248b8d43cdeb9866f1AMSPR06MB343eurprd06pro_";
        #   type="text/html"
        if not message.is_multipart() or message.get('content-type', '').startswith("text/"):
            encoding = message.get_content_charset()
            body = message.get_payload(decode=True)
            body = tools.ustr(body, encoding, errors='replace')
            if message.get_content_type() == 'text/plain':
                # text/plain -> <pre/>
                body = tools.append_content_to_html(u'', body, preserve=True)
        else:
            alternative = False
            mixed = False
            html = u''
            for part in message.walk():
                if part.get_content_type() == 'multipart/alternative':
                    alternative = True
                if part.get_content_type() == 'multipart/mixed':
                    mixed = True
                if part.get_content_maintype() == 'multipart':
                    continue  # skip container
                # part.get_filename returns decoded value if able to decode, coded otherwise.
                # original get_filename is not able to decode iso-8859-1 (for instance).
                # therefore, iso encoded attachements are not able to be decoded properly with get_filename
                # code here partially copy the original get_filename method, but handle more encoding
                filename = part.get_param('filename', None, 'content-disposition')
                if not filename:
                    filename = part.get_param('name', None)
                if filename:
                    if isinstance(filename, tuple):
                        # RFC2231
                        filename = email.utils.collapse_rfc2231_value(filename).strip()
                    else:
                        filename = tools.decode_smtp_header(filename)
                encoding = part.get_content_charset()  # None if attachment

                # 0) Inline Attachments -> attachments, with a third part in the tuple to match cid / attachment
                if filename and part.get('content-id'):
                    inner_cid = part.get('content-id').strip('><')
                    attachments.append(self._Attachment(filename, part.get_payload(decode=True), {'cid': inner_cid}))
                    continue
                # 1) Explicit Attachments -> attachments
                if filename or part.get('content-disposition', '').strip().startswith('attachment'):
                    if part.get_content_maintype() == 'message':
                        attachments.append(
                            self._Attachment(filename or 'attachment', part.get_payload(), {'message': True}))
                    else:
                        attachments.append(
                            self._Attachment(filename or 'attachment', part.get_payload(decode=True), {}))
                    continue
                # 2) text/plain -> <pre/>
                if part.get_content_type() == 'text/plain' and (not alternative or not body):
                    body = tools.append_content_to_html(body, tools.ustr(part.get_payload(decode=True),
                                                                         encoding, errors='replace'), preserve=True)
                # 3) text/html -> raw
                elif part.get_content_type() == 'text/html':
                    # mutlipart/alternative have one text and a html part, keep only the second
                    # mixed allows several html parts, append html content
                    append_content = not alternative or (html and mixed)
                    html = tools.ustr(part.get_payload(decode=True), encoding, errors='replace')
                    if not append_content:
                        body = html
                    else:
                        body = tools.append_content_to_html(body, html, plaintext=False)
                # 4) Anything else -> attachment
                else:
                    attachments.append(self._Attachment(filename or 'attachment', part.get_payload(decode=True), {}))

        body, attachments = self._message_extract_payload_postprocess(message, body, attachments)
        return body, attachments
