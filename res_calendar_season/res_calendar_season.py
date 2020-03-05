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

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _


class ResCalendarSeason(models.Model):
    _name = 'res.calendar.season'
    _order = 'sequence'

    sequence = fields.Integer(u"Sequence", required=True)
    name = fields.Char(u"Season's name", required=True)
    start_month_id = fields.Many2one('res.calendar.month', u"Start month")
    end_month_id = fields.Many2one('res.calendar.month', u"End month")
    period = fields.Char(u"period", compute='_compute_period')

    @api.multi
    def _compute_period(self):
        for rec in self:
            rec.period = _("%s to %s") % (rec.start_month_id.name, rec.end_month_id.name)

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, "%s (%s)" % (rec.name, rec.period)))
        return res

    @api.multi
    def _get_duration(self, year):
        self.ensure_one()
        today = date.today()
        start_date = today + relativedelta(year=year, month=self.start_month_id.number, day=1)
        end_date = today + relativedelta(year=year, month=self.end_month_id.number, day=31)
        return start_date, end_date

    @api.multi
    def get_months(self):
        self.ensure_one()
        today = date.today()
        current_date = today + relativedelta(month=self.start_month_id.number, day=1)
        list_month = []
        while current_date.month != self.end_month_id.number:
            list_month.append(current_date.month)
            current_date = current_date + relativedelta(months=1)
        list_month.append(self.end_month_id.number)
        return list_month
