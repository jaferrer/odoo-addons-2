# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from datetime import datetime

from odoo import fields, models, exceptions


class ResCompany(models.Model):
    _inherit = 'res.company'

    calendar_id = fields.Many2one('resource.calendar', string=u"Company Calendar")

    def schedule_working_days(self, nb_days, day_date):
        """Returns the date that is nb_days working days after day_date in the context of this company.

        :param nb_days: int: The number of working days to add to day_date. If nb_days is negative, counting is done
                             backwards.
        :param day_date: datetime: The starting date for the scheduling calculation.
        :return: The scheduled date nb_days after (or before) day_date.
        :rtype : datetime
        """
        self.ensure_one()
        assert isinstance(day_date, datetime)
        if nb_days == 0:
            return day_date
        elif nb_days > 0:
            # Hack to have today + 1 day = tomorrow instead of today after work
            nb_days += 1
        else:
            # Hack to have today - 1 day = yesterday instead of today before work
            nb_days -= 1
        calendar = self.calendar_id
        if not calendar:
            raise exceptions.UserError(u"You must define a calendar for this company to schedule productions.")
        newdate = calendar.schedule_days_get_date(nb_days, day_date=day_date, compute_leaves=True)
        if isinstance(newdate, (list, tuple)):
            newdate = newdate[0]
        return newdate
