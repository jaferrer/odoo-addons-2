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

from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.multi
    def _get_default_sms_message(self):
        return _(u"We remind you that you have an appointment on %(date)s at %(time)s with %(owner)s at %(location)s")

    sms_reminder_message = fields.Text(u"Calendar event reminder", default=_get_default_sms_message)
    sms_api_login = fields.Char("API login")
    sms_api_key = fields.Char("API key")
