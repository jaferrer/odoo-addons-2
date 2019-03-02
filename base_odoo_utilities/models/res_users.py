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

from odoo import fields, models


class ResUsers(models.Model):
    _name = 'res.users'

    def format_local_date(self, date=None):
        date_py = date or datetime.date.today()
        if isinstance(date_py, (str, unicode)):
            date_py = fields.Date.from_string(date_py)
        return date_py.strftime(self.env['res.lang'].search([('code', '=', self.env.user.lang)]).date_format)

    def format_local_datetime(self, date=None):
        date_py = date or datetime.datetime.now()
        if isinstance(date_py, (str, unicode)):
            date_py = fields.Datetime.from_string(date_py)
        lang = self.env['res.lang'].search([('code', '=', self.env.user.lang)])
        return date_py.strftime("%s %s" % (lang.date_format, lang.time_format))
