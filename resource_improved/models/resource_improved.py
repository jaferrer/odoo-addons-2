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

from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ResCompanyWithCalendar(models.Model):
    _inherit = "res.company"

    calendar_id = fields.Many2one("resource.calendar", "Company default calendar",
                                  help="The default calendar of the company to define working days. This calendar is "
                                       "used for locations outside warehouses or "
                                       "for warehouses without a calendar defined. If undefined here the default "
                                       "calendar will consider working days being Monday to Friday.")

    def schedule_working_days(self, nb_days, day_date):
        """ Return the date that is nb_days working days after day_date in the context of this company.

        :param nb_days: int: The number of working days to add to day_date. If nb_days is negative, counting is done
                             backwards.
        :param day_date: datetime: The starting date for the scheduling calculation.
        :return: The scheduled date nb_days after (or before) day_date.
        :rtype : datetime
        """
        self.ensure_one()

        if isinstance(day_date, str):
            day_date = fields.Datetime.from_string(day_date)
        elif isinstance(day_date, date):
            day_date = datetime.combine(day_date, datetime.min.time())
        elif not isinstance(day_date, datetime):
            raise UserError(_(u"Error : this function only accepts dates in date, datetime or string format !\n"
                              u"(%s was a %s)") % (day_date, type(day_date)))
        calendar = self.calendar_id
        if not calendar:
            # If the company hasn't a calendar, we count all days as working
            # Otherwise it was causing issues in sale_mrp tests
            return day_date + relativedelta(days=nb_days)
        newdate = calendar.schedule_days_get_date(nb_days, day_date=day_date, compute_leaves=True)
        if isinstance(newdate, (list, tuple)):
            newdate = newdate[0]
        return newdate


class DaysOfWeekTags(models.Model):
    _name = 'resource.day_of_week'
    _description = "Days of the week"

    name = fields.Char("Day of the week", index=True, required=True)
    code = fields.Integer("# day of the week", index=True, required=True)


class ResourceWorkingDays(models.Model):
    _inherit = 'resource.resource'

    leave_ids = fields.One2many('resource.calendar.leaves', 'resource_id', string="List of related leaves")


class LeavesWorkingDays(models.Model):
    _inherit = 'resource.calendar.leaves'

    @api.multi
    def onchange_resource(self, resource):
        result = super(LeavesWorkingDays, self).onchange_resource(resource)
        if self.env.context.get('default_resource_id'):
            return {'calendar_id': self.env.context['default_resource_id']}
        return result


class RessourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    @api.multi
    def schedule_days_get_date(self, days, day_date=None, compute_leaves=False, resource_id=None,
                               default_interval=None):
        """ Override resource.calendar method

        We add ore remove 1 to days in order to have `today + 1 day = tomorrow`
        Odoo native behaviour is `today + 1 day = today after work`

        If "today" is not a working day, we keep the +/- 1 day, because `today_not_working + 1 day of work` should not
        be the next working day, but the day after
        """
        self.ensure_one()
        if days == 0:
            return day_date
        elif days > 0:
            # Hack to have today + 1 day = tomorrow instead of today after work
            days += 1
        else:
            # Hack to have today - 1 day = yesterday instead of today before work
            days -= 1
        result = super(RessourceCalendar, self).schedule_days_get_date(days, day_date=day_date,
                                                                       compute_leaves=compute_leaves,
                                                                       resource_id=resource_id,
                                                                       default_interval=default_interval)
        return result

    @api.multi
    def get_start_day_date(self, date, leaves=None, compute_leaves=False, resource_id=None, default_interval=None):
        self.ensure_one()
        date_end_day = date.replace(hour=23, minute=59, second=59)
        list_intervals = self.get_working_intervals_of_day(end_dt=date_end_day, leaves=leaves,
                                                           compute_leaves=compute_leaves, resource_id=resource_id,
                                                           default_interval=default_interval)
        if list_intervals and list_intervals[0]:
            return min([interval[0] for interval in list_intervals[0]])
        return date.replace(hour=0, minute=0, second=0)

    @api.multi
    def get_end_day_date(self, date, leaves=None, compute_leaves=False, resource_id=None, default_interval=None):
        self.ensure_one()
        date_end_day = date.replace(hour=23, minute=59, second=59)
        list_intervals = self.get_working_intervals_of_day(end_dt=date_end_day, leaves=leaves,
                                                           compute_leaves=compute_leaves, resource_id=resource_id,
                                                           default_interval=default_interval)
        if list_intervals and list_intervals[0]:
            return max([interval[1] for interval in list_intervals[0]])
        return date_end_day

    @api.multi
    def get_next_day(self, day_date):
        """ Get following date of day_date, based on resource.calendar. If no
        calendar is provided, just return the next day.

        Override of the odoo method, because it didn't considered calendar with only ONE weekday in it

        :param date day_date: current day as a date

        :return date: next day of calendar, or just next day """
        if not self:
            return day_date + relativedelta(days=1)
        self.ensure_one()
        weekdays = self.get_weekdays()

        base_index = -1
        for weekday in weekdays:
            if weekday > day_date.weekday():
                break
            base_index += 1

        new_index = (base_index + 1) % len(weekdays)
        days = (weekdays[new_index] - day_date.weekday())
        if days <= 0:
            days = 7 + days

        return day_date + relativedelta(days=days)

    @api.multi
    def get_previous_day(self, day_date):
        """ Get previous date of day_date, based on resource.calendar. If no
        calendar is provided, just return the previous day.

        Override of the odoo method, because it didn't considered calendar with only ONE weekday in it

        :param date day_date: current day as a date

        :return date: previous day of calendar, or just previous day """
        if not self:
            return day_date + relativedelta(days=-1)
        self.ensure_one()
        weekdays = self.get_weekdays()
        weekdays.reverse()

        base_index = -1
        for weekday in weekdays:
            if weekday < day_date.weekday():
                break
            base_index += 1

        new_index = (base_index + 1) % len(weekdays)
        days = (weekdays[new_index] - day_date.weekday())
        if days >= 0:
            days = days - 7

        return day_date + relativedelta(days=days)
