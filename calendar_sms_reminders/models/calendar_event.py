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

import logging

from datetime import datetime, timedelta
from odoo import models, api, fields, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    send_sms_day_before = fields.Boolean(u"Send sms the day before")
    sms_reminder_send = fields.Boolean(u"Sms reminder send", readonly=True)

    @api.multi
    def action_open_sms_wizard(self):
        self.ensure_one()
        wizard = self.env['calendar.event.sms.wizard'].create({})
        wizard.populate(self)

        #  displays the pop-up
        return {
            'name': _(u'Send SMS'),
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event.sms.wizard',
            'res_id': wizard.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new'
        }

    @api.model
    def cron_send_reminder_sms(self):
        events_to_reminder = self.search([
            ('send_sms_day_before', '=', True), ('sms_reminder_send', '=', False),
            ('start_datetime', '>=', datetime.strftime(datetime.now() + timedelta(1), '%Y-%m-%d 00:00:00')),
            ('start_datetime', '<=', datetime.strftime(datetime.now() + timedelta(1), '%Y-%m-%d 23:59:00'))])

        for event in events_to_reminder:
            wizard = self.env['calendar.event.sms.wizard'].create({})
            wizard.populate(event)
            try:
                wizard.action_send_sms()
                event.sms_reminder_send = True
            except UserError as e:
                _logger.error('An error occurred while sending an SMS : %s', e)
