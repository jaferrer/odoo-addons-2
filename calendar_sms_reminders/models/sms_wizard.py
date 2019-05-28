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

from odoo import fields, models, api


class SmsWizard(models.TransientModel):
    _name = 'calendar.event.sms.wizard'

    calendar_event_id = fields.Many2one('calendar.event')
    """
    sms can be sent to the calendar event's attendees. theses last one are stored in domain_attendee_ids
    attendee_ids contains the list of attendees that will be notified by SMS
    """
    domain_attendee_ids = fields.Many2many('calendar.attendee')
    attendee_to_notify_ids = fields.Many2many('calendar.attendee')
    sms_message = fields.Char('SMS message', compute="_compute_sms_message")

    @api.multi
    def populate(self, calendar_event):
        self.calendar_event_id = calendar_event
        self.domain_attendee_ids = calendar_event.attendee_ids
        self.attendee_to_notify_ids = calendar_event.attendee_ids

    @api.depends('calendar_event_id')
    @api.multi
    def _compute_sms_message(self):
        for rec in self:
            rec.sms_message = self.env['calendar.attendee'].get_sms_message(rec.calendar_event_id, self.env.user.lang)

    @api.multi
    def action_send_sms(self):
        self.ensure_one()
        self.attendee_to_notify_ids.send_sms(self.calendar_event_id)
