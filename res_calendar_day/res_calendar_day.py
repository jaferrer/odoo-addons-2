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

from odoo import fields, models, api


class PoseMeetingLine(models.Model):
    _name = 'res.calendar.day'
    _description = "Calendar Day"
    _order = 'iso_week_day'

    name = fields.Char(u"Name", required=True, translate=True)
    iso_week_day = fields.Integer(u"ISO WeekDay", required=True)
    week_day = fields.Integer(u"Python WeekDay", required=True)
    is_weekend = fields.Boolean(u"Is WeekEnd", required=True)

    @api.model
    def _as_selection(self, domain=None, field_as_code=None):
        field_as_code = field_as_code or 'iso_week_day'
        result = self.search(domain or []).read(['name', field_as_code or 'iso_week_day'])
        return [(str(element[field_as_code]), element['name']) for element in result]
