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

import logging
import re
from email.message import Message

from odoo import models, api, tools
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
        """ Attempt to figure out the correct target model, thread_id, custom_values and user_id to use for an
        incoming message.
        Multiple values may be returned, if a message had multiple recipients matching existing mail.aliases, for
        example.

        ⚠️ Overwrite of the original odoo model, in order to split it into subfunctions, and to create the related model
        even if the incoming message is send as an answer in a thread ⚠️

        The following heuristics are used, in this order:

         * if the we have a related ``model``, an instance of it will be created from this message value, regardless of
           whether the mail is an answer to a thread or not
         * otherwise, we fallback to the typical behaviour of the original odoo method

        :param string message: an email.message instance
        :param dict message_dict: dictionary holding parsed message variables
        :param string model: the fallback model to use if the message does not match any of the currently configured
            mail aliases (may be None if a matching alias is supposed to be present)
        :param dict custom_values: optional dictionary of default field values to pass to ``message_new`` if a new
            record needs to be created. Ignored if the thread record already exists, and also if a matching mail.alias
            was found (aliases define their own defaults)
        :param int thread_id: optional ID of the record/thread from ``model`` to which this mail should be attached.
            Only used if the message does not reply to an existing thread and does not match any mail alias.
        :return: list of routes [(model, thread_id, custom_values, user_id, alias)]

        :raises: ValueError, TypeError
        """
        if not isinstance(message, Message):
            raise TypeError('message must be an email.message.Message at this point')

        # 0/ Init variables
        # =================
        dest_aliases = self.env['mail.alias']

        # get email.message.Message variables for future processing
        message_id = message.get('Message-Id')

        # compute references to find if message is a reply to an existing thread
        references = tools.decode_message_header(message, 'References')
        in_reply_to = tools.decode_message_header(message, 'In-Reply-To').strip()
        thread_references = references or in_reply_to
        _, reply_model, reply_thread_id, _, reply_private = tools.email_references(
            thread_references)

        # author and recipients
        email_from = tools.decode_message_header(message, 'From')
        email_from_localpart = (tools.email_split(email_from) or [''])[0].split('@', 1)[0].lower()
        email_to = tools.decode_message_header(message, 'To')
        email_to_localpart = (tools.email_split(email_to) or [''])[0].split('@', 1)[0].lower()

        # Delivered-To is a safe bet in most modern MTAs, but we have to fallback on To + Cc values
        # for all the odd MTAs out there, as there is no standard header for the envelope's `rcpt_to` value.
        rcpt_tos = ','.join([
            tools.decode_message_header(message, 'Delivered-To'),
            tools.decode_message_header(message, 'To'),
            tools.decode_message_header(message, 'Cc'),
            tools.decode_message_header(message, 'Resent-To'),
            tools.decode_message_header(message, 'Resent-Cc')])
        rcpt_tos_localparts = [e.split('@')[0].lower() for e in tools.email_split(rcpt_tos)]

        # 1/ Bounced Email
        # ================
        # Check if this is a bounced email and if so, do some things and return here
        if self.check_bounced(email_from_localpart, email_to_localpart, email_from, email_to, message, message_id):
            return []

        # 2/ Model
        # ========
        # If a model has been provided, we create an instance of it with the informations contained in this message
        if model:
            return self.handle_related_model(message, message_dict, model, thread_id, custom_values, email_from,
                                             email_to)

        # 3/ Thread reply
        # ===============
        msg_references = [ref for ref in tools.mail_header_msgid_re.findall(thread_references) if 'reply_to' not in ref]
        mail_messages = self.env['mail.message'].sudo().search([('message_id', 'in', msg_references)], limit=1)
        is_a_reply = bool(mail_messages)

        # 3.1/ Handle forward to an alias with a different model: do not consider it as a reply
        if reply_model and reply_thread_id:
            other_alias = self.env['mail.alias'].search([
                '&',
                ('alias_name', '!=', False),
                ('alias_name', '=', email_to_localpart)
            ])
            if other_alias and other_alias.alias_model_id.model != reply_model:
                is_a_reply = False

        if is_a_reply:
            model, thread_id = mail_messages.model, mail_messages.res_id
            if not reply_private:  # TDE note: not sure why private mode as no alias search, copying existing behavior
                dest_aliases = self.env['mail.alias'].search([('alias_name', 'in', rcpt_tos_localparts)], limit=1)

            route = self.message_route_verify(
                message, message_dict,
                (model, thread_id, custom_values, self._uid, dest_aliases),
                update_author=True, assert_model=reply_private, create_fallback=True,
                allow_private=reply_private, drop_alias=True)
            if route:
                _logger.info(u"Routing mail from %s to %s with Message-Id %s: direct reply to msg: model: %s, "
                             u"thread_id: %s, custom_values: %s, uid: %s", email_from, email_to, message_id, model,
                             thread_id, custom_values, self._uid)
                return [route]
            elif route is False:
                return []

        # 4/ Mail.alias
        # =============
        # Look for a matching mail.alias entry
        if rcpt_tos_localparts:
            alias_route = self.handle_alias(email_from, email_to, message, message_dict, message_id,
                                            rcpt_tos_localparts)
            if alias_route is not None:
                return alias_route

        # 5/ Error if neither route nor bounce
        # ====================================
        raise ValueError(
            'No possible route found for incoming message from %s to %s (Message-Id %s:). '
            'Create an appropriate mail.alias or force the destination model.' %
            (email_from, email_to, message_id)
        )

    def handle_alias(self, email_from, email_to, message, message_dict, message_id, rcpt_tos_localparts):
        # no route found for a matching reference (or reply), so parent is invalid
        message_dict.pop('parent_id', None)
        dest_aliases = self.env['mail.alias'].search([('alias_name', 'in', rcpt_tos_localparts)])
        if dest_aliases:
            routes = []
            for alias in dest_aliases:
                user_id = alias.alias_user_id.id
                if not user_id:
                    # TDE note: this could cause crashes, because no clue that the user
                    # that send the email has the right to create or modify a new document
                    # Fallback on user_id = uid
                    # Note: recognized partners will be added as followers anyway
                    # user_id = self._message_find_user_id(message)
                    user_id = self._uid
                    _logger.info('No matching user_id for the alias %s', alias.alias_name)
                route = (
                    alias.alias_model_id.model,
                    alias.alias_force_thread_id,
                    safe_eval(alias.alias_defaults),
                    user_id,
                    alias
                )
                route = self.message_route_verify(message, message_dict, route,
                                                  update_author=True, assert_model=True, create_fallback=True)
                if route:
                    _logger.info(
                        'Routing mail from %s to %s with Message-Id %s: direct alias match: %r',
                        email_from, email_to, message_id, route)
                    routes.append(route)
            return routes
        return None

    def check_bounced(self, email_from_localpart, email_to_localpart, email_from, email_to, message, message_id):
        bounce_alias = self.env['ir.config_parameter'].get_param("mail.bounce.alias")

        # 1.1 / Main test
        # ===============
        # Test if this email is a bounced email.
        # If so, use it to collect bounce data & update customers notifications
        if bounce_alias and bounce_alias in email_to_localpart:
            # Bounce regex: typical form of bounce is bounce_alias+128-crm.lead-34@domain
            # group(1) = the mail ID; group(2) = the model (if any); group(3) = the record ID
            bounce_re = re.compile(r"%s\+(\d+)-?([\w.]+)?-?(\d+)?" % re.escape(bounce_alias), re.UNICODE)
            bounce_match = bounce_re.search(email_to)

            if bounce_match:
                self.handle_bounce(bounce_match, email_from, email_to, message, message_id)
                return True

        # 1.2/ Another test
        # =================
        # Not sure why a second test for bounced message is needed
        #    See http://datatracker.ietf.org/doc/rfc3462/?include_text=1
        #    As all MTA does not respect this RFC (googlemail is one of them),
        #    we also need to verify if the message come from "mailer-daemon"
        if message.get_content_type() == 'multipart/report' or email_from_localpart == 'mailer-daemon':
            _logger.info('Routing mail with Message-Id %s: not routing bounce email from %s to %s',
                         message_id, email_from, email_to)
            return True

        return False

    def handle_bounce(self, bounce_match, email_from, email_to, message, message_id):
        bounced_mail_id, bounced_model, bounced_thread_id = bounce_match.group(1), bounce_match.group(
            2), bounce_match.group(3)
        email_part = next((part for part in message.walk() if part.get_content_type() == 'message/rfc822'), None)
        dsn_part = next((part for part in message.walk() if part.get_content_type() == 'message/delivery-status'), None)
        partners, partner_address = self.env['res.partner'], False
        if dsn_part and len(dsn_part.get_payload()) > 1:
            dsn = dsn_part.get_payload()[1]
            final_recipient_data = tools.decode_message_header(dsn, 'Final-Recipient')
            partner_address = final_recipient_data.split(';', 1)[1].strip()
            if partner_address:
                partners = partners.sudo().search([('email', 'like', partner_address)])
                for partner in partners:
                    partner.message_receive_bounce(partner_address, partner, mail_id=bounced_mail_id)
        mail_message = self.env['mail.message']
        if email_part:
            email = email_part.get_payload()[0]
            bounced_message_id = tools.mail_header_msgid_re.findall(tools.decode_message_header(email, 'Message-Id'))
            mail_message = mail_message.sudo().search([('message_id', 'in', bounced_message_id)])
        if partners and mail_message:
            notifications = self.env['mail.notification'].sudo().search([
                ('mail_message_id', '=', mail_message.id),
                ('res_partner_id', 'in', partners.ids)])
            notifications.write({
                'email_status': 'bounce'
            })
        if bounced_model in self.env and hasattr(self.env[bounced_model],
                                                 'message_receive_bounce') and bounced_thread_id:
            self.env[bounced_model].browse(int(bounced_thread_id)).message_receive_bounce(partner_address, partners,
                                                                                          mail_id=bounced_mail_id)
        _logger.info(u"Routing mail from %s to %s with Message-Id %s: bounced mail from mail %s, model: %s, thread_id: "
                     u"%s: dest %s (partner %s)", email_from, email_to, message_id, bounced_mail_id, bounced_model,
                     bounced_thread_id, partner_address, partners)

    def handle_related_model(self, message, message_dict, model, thread_id, custom_values, email_from, email_to):
        # no route found for a matching reference (or reply), so parent is invalid
        message_dict.pop('parent_id', None)
        route = self.message_route_verify(message, message_dict, (model, thread_id, custom_values, self._uid, None),
                                          update_author=True, assert_model=True)
        if route:
            _logger.info(u"Routing mail from %s to %s with Message-Id %s: fallback to model:%s, thread_id:%s, "
                         u"custom_values:%s, uid:%s", email_from, email_to, message.get('Message-Id'), model, thread_id,
                         custom_values, self._uid)
            return [route]

        return []
