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

from openerp import fields, models, api, _


class ResCompanyWithCalendar(models.Model):
    _inherit = "res.company"

    calendar_id = fields.Many2one("resource.calendar", "Company default calendar",
                                  help="The default calendar of the company to define working days. This calendar is "
                                       "used for locations outside warehouses or "
                                       "for warehouses without a calendar defined. If undefined here the default "
                                       "calendar will consider working days being Monday to Friday.")

    @api.multi
    def schedule_working_days(self, nb_days, day_date):
        """Returns the date that is nb_days working days after day_date in the context of the current company.

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
        calendar = self.calendar_id
        if not calendar:
            calendar = self.env.ref("resource_improved.default_calendar")
        newdate = calendar.schedule_days_get_date(nb_days, day_date=day_date,
                                                  resource_id=False,
                                                  compute_leaves=True)
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


class PreComputedCalendarDelays(models.Model):
    _name = 'pre.computed.calendar.delays'

    days = fields.Integer(string=u"Nb of days")
    day_date = fields.Date(string=u"Day date")
    compute_leaves = fields.Boolean(string=u"Compute leaves")
    resource_id = fields.Integer(string=u"Resource ID")
    default_interval = fields.Char(string=u"Default interval")
    result = fields.Datetime(string=u"Scheduled day")

    @api.model
    def sweep_table(self):
        self.env.cr.execute("""TRUNCATE TABLE pre_computed_calendar_delays RESTART IDENTITY;""")


class RessourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    @api.multi
    def schedule_days_get_date(self, days, day_date=None, compute_leaves=False, resource_id=None,
                               default_interval=None):
        if days < 0:
            days -= 1
        self.ensure_one()
        do_not_save_result = self.env.context.get('do_not_save_result')
        domain = [('days', '=', days or 0),
                  ('day_date', '=', day_date and fields.Date.to_string(day_date) or False),
                  ('compute_leaves', '=', compute_leaves),
                  ('resource_id', '=', resource_id or 0),
                  ('default_interval', '=', default_interval and str(default_interval) or False)]
        pre_compute_result = self.env['pre.computed.calendar.delays'].sudo().search(domain, limit=1)
        if pre_compute_result:
            result = [fields.Datetime.from_string(pre_compute_result.sudo().result)]
        else:
            result = super(RessourceCalendar, self).schedule_days_get_date(days, day_date=day_date,
                                                                           compute_leaves=compute_leaves,
                                                                           resource_id=resource_id,
                                                                           default_interval=default_interval)
            date = result
            if isinstance(result, (list, tuple)):
                date = result[0]
            if not do_not_save_result:
                dict_result = {'days': days or 0,
                               'day_date': day_date and fields.Date.to_string(day_date) or False,
                               'compute_leaves': compute_leaves,
                               'resource_id': resource_id or False,
                               'default_interval': default_interval and str(default_interval) or False,
                               'result': fields.Datetime.to_string(date)}
                self.env['pre.computed.calendar.delays'].sudo().create(dict_result)
        return result

    @api.multi
    def get_start_day_date(self, date, leaves=None, compute_leaves=False, resource_id=None, default_interval=None):
        self.ensure_one()
        date_end_day = date.replace(hour=23, minute=59, second=59)
        list_intervals = self.get_working_intervals_of_day(end_dt=date_end_day, leaves=leaves,
                                                           compute_leaves=compute_leaves, resource_id=resource_id,
                                                           default_interval=default_interval)
        return min([interval[0] for interval in list_intervals[0]])

    @api.multi
    def get_end_day_date(self, date, leaves=None, compute_leaves=False, resource_id=None, default_interval=None):
        self.ensure_one()
        date_end_day = date.replace(hour=23, minute=59, second=59)
        list_intervals = self.get_working_intervals_of_day(end_dt=date_end_day, leaves=leaves,
                                                           compute_leaves=compute_leaves, resource_id=resource_id,
                                                           default_interval=default_interval)
        return max([interval[1] for interval in list_intervals[0]])
