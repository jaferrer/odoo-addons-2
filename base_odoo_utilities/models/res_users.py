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

import datetime
import pytz

from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def format_local_date(self, date=None):
        date_py = date or datetime.date.today()
        if isinstance(date_py, (str, unicode)):
            date_py = fields.Date.from_string(date_py)
        lang = self.env['res.lang'].search([('code', '=', self.first().lang or self.env.user.lang)])
        return date_py.strftime(lang.date_format)

    @api.multi
    def format_local_datetime(self, date=None):
        date_py = date or datetime.datetime.now()
        if isinstance(date_py, (str, unicode)):
            date_py = fields.Datetime.from_string(date_py)
        lang = self.env['res.lang'].search([('code', '=', self.first().lang or self.env.user.lang)])
        return date_py.strftime("%s %s" % (lang.date_format, lang.time_format))

    @api.multi
    def utcize_date(self, date_dt):
        """Return UTC date of given date (as dt)"""
        self.ensure_one()
        tz_info = fields.Datetime.context_timestamp(self, date_dt).tzinfo
        dt_utc = date_dt.replace(tzinfo=tz_info).astimezone(pytz.UTC).replace(tzinfo=None)
        return dt_utc

    @api.multi
    def localize_date(self, date_dt):
        """Return TZ date of given UTC date (as dt)"""
        self.ensure_one()
        tz_info = fields.Datetime.context_timestamp(self, date_dt).tzinfo
        dt_loc = date_dt.replace(tzinfo=pytz.UTC).astimezone(tz_info).replace(tzinfo=None)
        return dt_loc


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.multi
    def format_local_date(self, date=None):
        return self.partner_id.format_local_date(date)

    @api.multi
    def format_local_datetime(self, date=None):
        return self.partner_id.format_local_datetime(date)

    @api.multi
    def utcize_date(self, date_dt):
        return self.partner_id.utcize_date(date_dt)

    @api.multi
    def localize_date(self, date_dt):
        return self.partner_id.localize_date(date_dt)
