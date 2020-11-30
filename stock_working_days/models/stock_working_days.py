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

from odoo import fields, models, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


class StockWarehouseWithCalendar(models.Model):
    _inherit = "stock.warehouse"

    view_location_id = fields.Many2one('stock.location', index=True)
    resource_id = fields.Many2one("resource.resource", "Warehouse resource",
                                  help="The resource is used to define the working days of the warehouse. If undefined "
                                       "the system will fall back to the default company calendar.")


class StockWorkingDaysLocation(models.Model):
    _inherit = 'stock.location'

    @api.model
    def get_warehouse(self, location=None):
        """ Return warehouse id of warehouse that contains location

        overridden here for improved performance

        :param location: browse record (stock.location)
        """
        location = location or self
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
        return self.env['stock.warehouse'].browse(whs and whs[0] or False)

    @api.multi
    def schedule_working_days(self, nb_days, day_date, days_of_week=False):
        """ Return the date that is nb_days working days after day_date in the context of the current location.

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
        warehouse = self.get_warehouse(self)
        resource = warehouse.resource_id
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
            day_codes = {d.code for d in days_of_week}
            if day_codes:
                if newdate.weekday() not in day_codes:
                    if nb_days > 0:
                        newdate = min(newdate + relativedelta(weekday=weekdays[dow]) for dow in day_codes)
                    else:
                        newdate = max(newdate + relativedelta(weekday=weekdays[dow](-1)) for dow in day_codes)

        return newdate


class FixedDaysProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    days_of_week = fields.Many2many('resource.day_of_week', string="Fixed days of week",
                                    help="Set here the days of the week on which this rule can be trigerred. Leave "
                                         "empty for moves that can be performed on any day of the week.")


class ProcurementWorkingDays(models.Model):
    _inherit = "procurement.order"

    @api.model
    def _get_stock_move_values(self):
        """ Return a dictionary of values that will be used to create a stock move from a procurement.
        This function assumes that the given procurement has a rule (action == 'move') set on it.
        Overridden to calculate dates taking into account the applicable working days calendar.

        :rtype: dictionary
        """
        vals = super(ProcurementWorkingDays, self)._get_stock_move_values()
        proc_date = datetime.strptime(self.date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
        location = self.location_id or self.warehouse_id.view_location_id
        newdate = location.schedule_working_days(-self.rule_id.delay or 0,
                                                 proc_date,
                                                 self.rule_id.days_of_week)
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


class StockLocationPathWorkingDays(models.Model):
    _inherit = 'stock.location.path'

    @api.model
    def _prepare_push_apply(self, rule, move):
        res = super(StockLocationPathWorkingDays, self)._prepare_push_apply(rule, move)
        date = datetime.strptime(move.date_expected, DEFAULT_SERVER_DATETIME_FORMAT)
        newdate = move.location_dest_id.schedule_working_days(rule.delay + 1 or 0, date)
        res.update({
            'date': newdate.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'date_expected': newdate.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        })
        return res

    @api.model
    def _apply(self, move):
        date = datetime.strptime(move.date_expected, DEFAULT_SERVER_DATETIME_FORMAT)
        newdate = move.location_dest_id.schedule_working_days(self.delay or 0, date)
        newdate = newdate.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        if self.auto == 'transparent':
            move.write({
                'date': newdate,
                'date_expected': newdate,
                'location_dest_id': self.location_dest_id.id
            })
            # avoid looping if a push rule is not well configured
            if self.location_dest_id.id != move.location_dest_id.id:
                # call again push_apply to see if a next step is defined
                self.env['stock.move']._push_apply(move)
        else:
            new_move_vals = self._prepare_move_copy_values(move, newdate)
            new_move = move.copy(new_move_vals)
            move.write({'move_dest_id': new_move.id})
            new_move.action_confirm()
