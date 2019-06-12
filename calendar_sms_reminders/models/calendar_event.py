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
from odoo import models, api, _


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

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
