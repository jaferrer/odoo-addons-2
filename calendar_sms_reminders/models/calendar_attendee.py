# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import uuid
import phonenumbers
from octopush import SMS, SMS_WORLD
from odoo.exceptions import UserError
from odoo import fields, models, api, _


class CalendarAttendee(models.Model):
    _inherit = 'calendar.attendee'

    mobile = fields.Char(u"Mobile phone", related='partner_id.mobile')
    is_mobile_phone_correct = fields.Boolean("mobile phone defined", compute="_compute_is_mobile_phone_correct")
    sms_date_sent = fields.Datetime(u"Date SMS", readonly=True)

    @api.multi
    def _compute_is_mobile_phone_correct(self):
        for rec in self:
            if rec.mobile and rec.partner_id.country_id.code:
                phone_number = phonenumbers.parse(rec.mobile, rec.partner_id.country_id.code)
                rec.is_mobile_phone_correct = phonenumbers.is_valid_number(phone_number)

    @api.multi
    def get_sms_message(self, calendar_event, lang_code):
        """ format the sms message using res_lang to set date time format res_lang depends on the attendee """
        sms_message = self.env.user.company_id.sms_reminder_message

        res_lang = self.env['res.lang'].search([('code', '=', lang_code)])
        date_mask = res_lang.date_format
        time_mask = res_lang.time_format
        event_date = fields.Datetime.from_string(calendar_event.start_datetime)
        return sms_message % {
            'date': event_date.strftime(date_mask),
            'time': event_date.strftime(time_mask),
            'owner': calendar_event.user_id.display_name,
            'location': calendar_event.location or ""
        }

    @api.multi
    def send_sms(self, calendar_event):
        """ Send mail for event invitation to event attendees.
            :param calendar_event: related event
        """
        sms_login = self.env.user.company_id.sms_api_login
        sms_key = self.env.user.company_id.sms_api_key

        if not sms_login or not sms_key:
            raise UserError(_(u'Please set the sms API key and login in the company settings'))

        for attendee in self:
            if attendee.is_mobile_phone_correct:
                sms = SMS(sms_login, sms_key)
                sms.set_sms_text(self.get_sms_message(calendar_event, attendee.partner_id.lang))
                sms.set_sms_recipients([attendee.mobile])
                sms.set_sms_type(SMS_WORLD)
                sms.set_sms_sender(self.env.user.company_id.display_name)
                sms.set_sms_request_id(str(uuid.uuid1()))
                try:
                    result = sms.send()
                    if result:
                        attendee.sms_date_sent = fields.Datetime.now()
                except Exception as ex:
                    raise UserError('Octopush: sending sms to [%s] failed, details : %s' % (attendee.mobile, ex))
