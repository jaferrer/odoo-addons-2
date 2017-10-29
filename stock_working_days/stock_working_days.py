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
from dateutil.relativedelta import relativedelta, weekdays

from openerp import fields, models, api, _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


class stock_warehouse_with_calendar(models.Model):
    _inherit = "stock.warehouse"

    view_location_id = fields.Many2one('stock.location', index=True)
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

            overridden here for improved performance
        """
        query = """
            SELECT swh.id
            FROM
                stock_warehouse swh
                LEFT JOIN stock_location sl ON swh.view_location_id = sl.id
            WHERE
                sl.parent_left <= %s AND sl.parent_right >= %s
            ORDER BY swh.id
            LIMIT 1
        """
        self.env.cr.execute(query, (location.parent_left, location.parent_left))
        whs = self.env.cr.fetchone()
        return whs and whs[0] or False

    @api.multi
    def schedule_working_days(self, nb_days, day_date, days_of_week=False):
        """Returns the date that is nb_days working days after day_date in the context of the current location.

        :param nb_days: int: The number of working days to add to day_date. If nb_days is negative, counting is done
                             backwards.
        :param day_date: datetime: The starting date for the scheduling calculation.
        :param days_of_week: a recorset of resource.day_of_week on which the returned date must be. If it is not, it
        will increase abs(nb_days) until it does if nb_days.
        :return: The scheduled date nb_days after (or before) day_date.
        :rtype : datetime
        """
        self.ensure_one()
        assert isinstance(day_date, datetime)
        if nb_days == 0:
            return day_date
        warehouse = self.env['stock.warehouse'].browse(self.get_warehouse(self))
        resource = warehouse and warehouse.resource_id or False
        if resource:
            calendar = resource.calendar_id
        else:
            calendar = self.company_id.calendar_id
        if not calendar:
            calendar = self.env.ref("resource_improved.default_calendar")
        newdate = calendar.schedule_days_get_date(nb_days, day_date=day_date,
                                                  resource_id=resource and resource.id or False,
                                                  compute_leaves=True)
        if isinstance(newdate, (list, tuple)):
            newdate = newdate[0]

        # Check if this is to be done only on some days of the week
        if days_of_week:
            day_codes = [d.code for d in days_of_week]
            if len(day_codes) != 0:
                dates = []
                for dow in day_codes:
                    if newdate + relativedelta(weekday=weekdays[dow]) == newdate:
                        dates = [newdate]
                        break
                    if nb_days > 0:
                        dates.append(newdate + relativedelta(weekday=weekdays[dow]))
                    else:
                        dates.append(newdate + relativedelta(weekday=weekdays[dow](-1)))
                newdate = max(dates)

        return newdate


class fixed_days_procurement_rule(models.Model):
    _inherit = 'procurement.rule'

    days_of_week = fields.Many2many('resource.day_of_week', string="Fixed days of week",
                                    help="Set here the days of the week on which this rule can be trigerred. Leave "
                                         "empty for moves that can be performed on any day of the week.")


class procurement_working_days(models.Model):
    _inherit = "procurement.order"

    @api.model
    def _run_move_create(self, procurement):
        ''' Returns a dictionary of values that will be used to create a stock move from a procurement.
        This function assumes that the given procurement has a rule (action == 'move') set on it.
        Overridden to calculate dates taking into account the applicable working days calendar.

        :param procurement: browse record
        :rtype: dictionary
        '''
        vals = super(procurement_working_days, self)._run_move_create(procurement)
        proc_date = datetime.strptime(procurement.date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
        location = procurement.location_id or procurement.warehouse_id.view_location_id
        newdate = location.schedule_working_days(-procurement.rule_id.delay or 0,
                                                 proc_date,
                                                 procurement.rule_id.days_of_week)
        if newdate:
            vals.update({'date': newdate.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                         'date_expected': newdate.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        return vals

    @api.model
    def _get_orderpoint_date_planned(self, orderpoint, start_date):
        location = orderpoint.location_id or orderpoint.warehouse_id.view_location_id
        seller_delay = orderpoint.product_id.seller_ids and orderpoint.product_id.seller_ids[0].delay
        newdate = location.schedule_working_days(seller_delay or 0.0, start_date)
        return newdate.strftime(DEFAULT_SERVER_DATE_FORMAT)


class stock_location_path_working_days(models.Model):
    _inherit = 'stock.location.path'

    @api.model
    def _prepare_push_apply(self, rule, move):
        res = super(stock_location_path_working_days, self)._prepare_push_apply(rule, move)
        date = datetime.strptime(move.date_expected, DEFAULT_SERVER_DATETIME_FORMAT)
        newdate = move.location_dest_id.schedule_working_days(rule.delay + 1 or 0, date)
        res.update({
            'date': newdate.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'date_expected': newdate.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        })
        return res

    @api.model
    def _apply(self, rule, move):
        if rule.auto == 'transparent':
            date = datetime.strptime(move.date_expected, DEFAULT_SERVER_DATETIME_FORMAT)
            newdate = move.location_dest_id.schedule_working_days(rule.delay + 1 or 0, date)
            old_dest_location = move.location_dest_id.id
            move.write({
                'date': newdate.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'date_expected': newdate.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'location_dest_id': rule.location_dest_id.id
            })
            # avoid looping if a push rule is not well configured
            if rule.location_dest_id.id != old_dest_location:
                # call again push_apply to see if a next step is defined
                self.env['stock.move']._push_apply(move)
        else:
            super(stock_location_path_working_days, self)._apply(rule, move)


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
