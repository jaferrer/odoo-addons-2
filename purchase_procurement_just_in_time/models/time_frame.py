# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from dateutil.relativedelta import relativedelta, MO, SU

from openerp import models, fields, api
from openerp.tools import config


class procurement_time_frame(models.Model):
    _name = 'procurement.time.frame'

    name = fields.Char(required=True)
    nb = fields.Integer("Number")
    period_type = fields.Selection(
        [('days', "Day(s)"), ('weeks', "Week(s)"), ('months', "Month(s)"), ('years', "Year(s)")])

    @api.multi
    def get_start_end_dates(self, date, date_ref=False):
        self.ensure_one()
        if config['test_enable'] and not self.env.context.get("testing_date_ref"):
            date_ref = False
        delta = 0
        if date_ref:
            ds_start, ds_end = self._get_interval(date_ref)
            delta = (date_ref - ds_start).days
        real_start, real_end = self._get_interval(date - relativedelta(days=delta))
        real_start = real_start + relativedelta(days=delta)
        real_end = real_end + relativedelta(days=delta)
        return real_start, real_end

    @api.multi
    def _get_interval(self, date):
        """Returns the start and end dates of the time frame including date.
        @param self: object pointer,
        @param date: datetime object,
        @return: A tuple of datetime objects."""

        self.ensure_one()
        if self.period_type == 'days':
            doy = date.timetuple().tm_yday
            date_start = date + relativedelta(days=-((doy - 1) % self.nb), hour=0, minute=0, second=0)
            date_end = date_start + relativedelta(days=self.nb - 1, hour=23, minute=59, second=59)
        elif self.period_type == 'weeks':
            woy = date.isocalendar()[1]
            date_start = date + relativedelta(weeks=-((woy - 1) % self.nb) - 1, days=1, weekday=MO,
                                              hour=0, minute=0, second=0)
            date_end = date_start + relativedelta(weeks=self.nb - 1, weekday=SU, hour=23, minute=59, second=59)
        elif self.period_type == 'months':
            month = date.month
            date_start = date + relativedelta(months=-((month - 1) % self.nb), day=1, hour=0, minute=0, second=1)
            date_end = date_start + relativedelta(months=self.nb - 1, day=31, hour=23, minute=59, second=59)
        elif self.period_type == 'years':
            year = date.year
            date_start = date + relativedelta(years=-((year - 1) % self.nb), month=1, day=1, hour=0, minute=0, second=1)
            date_end = date_start + relativedelta(years=self.nb - 1, month=12, day=31, hour=23, minute=59, second=59)
        return date_start, date_end

    @api.multi
    def get_date_end_period(self, date_start):
        """
        :param date: datetime
        :return: datetime
        """
        self.ensure_one()
        date_end_period = date_start
        if self.period_type == 'days':
            date_end_period = date_start + relativedelta(days=self.nb)
        elif self.period_type == 'weeks':
            date_end_period = date_start + relativedelta(weeks=self.nb)
        elif self.period_type == 'months':
            date_end_period = date_start + relativedelta(months=self.nb)
        elif self.period_type == 'years':
            date_end_period = date_start + relativedelta(years=self.nb)
        return date_end_period
