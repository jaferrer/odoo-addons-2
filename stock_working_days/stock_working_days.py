# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from dateutil.relativedelta import relativedelta, weekdays

from openerp import fields, models, api, _
from openerp.exceptions import except_orm
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


###################################################################################################
# TODO: This should be removed as soon as https://github.com/odoo/odoo/pull/4030 is pulled upstream
class resource_calendar_bugfix(models.Model):
    """This is only while waiting for upstream bugfix."""
    _inherit = "resource.calendar"

    def _schedule_days(self, cr, uid, id, days, day_date=None, compute_leaves=False,
                       resource_id=None, default_interval=None, context=None):
        """Schedule days of work, using a calendar and an optional resource to
        compute working and leave days. This method can be used backwards, i.e.
        scheduling days before a deadline.
        :param int days: number of days to schedule. Use a negative number to
                         compute a backwards scheduling.
        :param date day_date: reference date to compute working days. If days is > 0
                              date is the starting date. If days is < 0 date is the
                              ending date.
        :param boolean compute_leaves: if set, compute the leaves based on calendar
                                       and resource. Otherwise no leaves are taken
                                       into account.
        :param int resource_id: the id of the resource to take into account when
                                computing the leaves. If not set, only general
                                leaves are computed. If set, generic and
                                specific leaves are computed.
        :param tuple default_interval: if no id, try to return a default working
                                       day using default_interval[0] as beginning
                                       hour, and default_interval[1] as ending hour.
                                       Example: default_interval = (8, 16).
                                       Otherwise, a void list of working intervals
                                       is returned when id is None.
        :return tuple (datetime, intervals): datetime is the beginning/ending date
                                             of the schedulign; intervals are the
                                             working intervals of the scheduling.
        Implementation note: rrule.rrule is not used because rrule it des not seem
        to allow getting back in time.
        """
        if day_date is None:
            day_date = datetime.datetime.now()
        backwards = (days < 0)
        days = abs(days)
        intervals = []
        planned_days = 0
        iterations = 0
        current_datetime = day_date.replace(hour=0, minute=0, second=0)
        if backwards:
            current_datetime = self.get_previous_day(cr, uid, id, current_datetime, context)

        while planned_days < days and iterations < 1000:
            working_intervals = self.get_working_intervals_of_day(
                cr, uid, id, current_datetime,
                compute_leaves=compute_leaves, resource_id=resource_id,
                default_interval=default_interval,
                context=context)
            if id is None or working_intervals:  # no calendar -> no working hours, but day is considered as worked
                planned_days += 1
                intervals += working_intervals
            # get next day
            if backwards:
                current_datetime = self.get_previous_day(cr, uid, id, current_datetime, context)
            else:
                current_datetime = self.get_next_day(cr, uid, id, current_datetime, context)
            # avoid infinite loops
            iterations += 1
        return intervals
###################################################################################################


class res_company_with_calendar(models.Model):
    _inherit = "res.company"

    calendar_id = fields.Many2one("resource.calendar", "Company default calendar",
                                  help="The default calendar of the company to define working days. This calendar is "
                                       "used for locations outside warehouses or "
                                       "for warehouses without a calendar defined. If undefined here the default "
                                       "calendar will consider working days being Monday to Friday.")


class stock_warehouse_with_calendar(models.Model):
    _inherit = "stock.warehouse"

    resource_id = fields.Many2one("resource.resource", "Warehouse resource",
                                  help="The resource is used to define the working days of the warehouse. If undefined "
                                       "the system will fall back to the default company calendar.")


class stock_working_days_location(models.Model):
    _inherit = 'stock.location'

    @api.model
    def get_warehouse(self, location):
        """
            Returns warehouse id of warehouse that contains location
            :param location: browse record (stock.location)

            Overridden here to have an implementation that checks at all levels of location tree.
        """
        wh_views = {w.view_location_id.id: w for w in self.env['stock.warehouse'].search([])}
        loc = location
        while loc:
            if loc.id in wh_views.keys():
                return wh_views[loc.id].id
            loc = loc.location_id
        return False


class days_of_week_tags(models.Model):
    _name = 'resource.day_of_week'
    _description = "Days of the week"

    name = fields.Char("Day of the week", index=True, required=True)
    code = fields.Integer("# day of the week", index=True, required=True)


class fixed_days_procurement_rule(models.Model):
    _inherit = 'procurement.rule'

    days_of_week = fields.Many2many('resource.day_of_week', string="Fixed days of week",
                                    help="Set here the days of the week on which this rule can be trigerred. Leave "
                                         "empty for moves that can be performed on any day of the week.")


class procurement_working_days(models.Model):
    _inherit = "procurement.order"

    @api.model
    def _schedule_working_days(self, days, day_date, resource, calendar):
        """Wrapper to call resource.calendar.schedule_days_get_date.

        :param int days: number of days to schedule. Negative if backwards
        :param datetime day_date: date to start scheduling from
        :param record resource: resource to calculate specific leaves. If false, only general leaves are counted
        :param record calendar: calendar to schedul on
        :rtype datetime
        """
        if days == 0:
            return day_date
        if calendar:
            newdate = calendar.schedule_days_get_date(days, day_date=day_date,
                                                      resource_id=resource and resource.id or False,
                                                      compute_leaves=True)
        else:
            raise except_orm(_("No calendar found!"),_("No calendar has been found to compute scheduling."))
        # For some reason call with new api returns a list of 1 date instead of the date
        if isinstance(newdate, (list, tuple)):
            newdate = newdate[0]
        return newdate

    def _get_move_calendar(self):
        """Returns the applicable (calendar, resource) tuple to use for stock move delay.
        The applicable calendar is the calendar of the warehouse resource if the location is in a warehouse and this
        warehouse has a resource, otherwise the company default calendar if it exists or the module's default calendar
        which considers workings days as being Monday to Friday.
        The applicable resource is the warehouse's resource if defined."""
        if self.location_id:
            warehouse_id = self.env['stock.warehouse'].browse(self.location_id.get_warehouse(self.location_id))
        else:
            warehouse_id = self.warehouse_id
        resource_id = warehouse_id and warehouse_id.resource_id or False
        if resource_id:
            calendar_id = warehouse_id.resource_id.calendar_id
        else:
            calendar_id = self.env.user.company_id.calendar_id
        if not calendar_id:
            calendar_id = self.env.ref("stock_working_days.default_calendar")
        return calendar_id, resource_id

    @api.model
    def _run_move_create(self, procurement):
        ''' Returns a dictionary of values that will be used to create a stock move from a procurement.
        This function assumes that the given procurement has a rule (action == 'move') set on it.
        Overridden to calculate dates taking into account the applicable working days calendar.

        :param procurement: browse record
        :rtype: dictionary
        '''
        vals = super(procurement_working_days, self)._run_move_create(procurement)
        calendar_id, resource_id = procurement._get_move_calendar()
        proc_date = datetime.strptime(procurement.date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
        newdate = procurement._schedule_working_days(-procurement.rule_id.delay or 0,
                                                     proc_date,
                                                     resource_id,
                                                     calendar_id)
        # Check if this is to be done only on some days of the week
        day_codes = [d.code for d in procurement.rule_id.days_of_week]
        if len(day_codes) != 0:
            dates = []
            for dow in day_codes:
                if newdate + relativedelta(weekday=weekdays[dow]) == newdate:
                    dates=[newdate]
                    break
                dates.append(newdate + relativedelta(weekday=weekdays[dow](-1)))
            newdate = max(dates)
        if newdate:
            vals.update({'date': newdate.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                         'date_expected': newdate.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        return vals
