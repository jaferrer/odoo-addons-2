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

from odoo import models, api, exceptions, fields


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.multi
    def write(self, vals):
        for rec in self:
            if not rec.workorder_ids:
                continue
            if 'date_planned_start' in vals and \
                    vals['date_planned_finished'] < max(w.date_planned_finished for w in rec.workorder_ids):
                raise exceptions.UserError(u"You cannot set the planned end date of a production order after "
                                           u"the latest end date of its work orders.")
            if 'date_planned_finished' in vals and \
                    vals['date_planned_start'] > min(w.date_planned_start for w in rec.workorder_ids):
                raise exceptions.UserError(u"You cannot set the planned start date of a production order after "
                                           u"the earliest start date of its work orders.")
        return super(MrpProduction, self).write(vals)

    @api.multi
    def _generate_workorders(self, exploded_boms):
        self.ensure_one()
        workorders = super(MrpProduction, self)._generate_workorders(exploded_boms)
        if not workorders:
            return workorders
        last_orders = workorders.filtered(lambda w: not w.next_work_order_id)
        for workorder in last_orders:
            date_end = self.date_planned_finished
            current = workorder
            while current:
                current.date_planned_finished = date_end
                date_start = current.workcenter_id.schedule_working_hours(-current.duration_expected / 60.0,
                                                                          fields.Datetime.from_string(date_end))
                current.date_planned_start = date_start
                date_end = fields.Datetime.to_string(date_start)
                current = current.previous_workorder_ids and current.previous_workorder_ids[0] or False


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    previous_workorder_ids = fields.One2many('mrp.workorder', 'next_work_order_id', u"Previous Work Order(s)")

    @api.multi
    @api.constrains('date_planned_start', 'date_planned_finished', 'duration_expected')
    def _check_dates_duration(self):
        for rec in self:
            if not rec.date_planned_start or not rec.date_planned_finished:
                continue
            dps = fields.Datetime.from_string(rec.date_planned_start)
            dpf = fields.Datetime.from_string(rec.date_planned_finished)
            computed_date_end = rec.workcenter_id.schedule_working_hours(rec.duration_expected / 60.0, dps)
            if rec.workcenter_id.calendar_id.get_working_hours(dpf, computed_date_end):
                raise exceptions.ValidationError(u"The difference between the planned start date and end date must be "
                                                 u"at least the expected duration.\n"
                                                 u"Expected duration: %s\n"
                                                 u"Date start: %s\n"
                                                 u"Date end: %s\n"
                                                 u"Expected end date: %s" % (rec.duration_expected, dps, dpf,
                                                                             computed_date_end))

    @api.multi
    def write(self, vals):
        res = super(MrpWorkorder, self).write(vals)
        for rec in self:
            # Sync end dates with next work order start dates and production end date
            if 'date_planned_finished' in vals:
                if rec.next_work_order_id:
                    if rec.next_work_order_id.date_planned_start < vals['date_planned_finished']:
                        rec.next_work_order_id.date_planned_start = vals['date_planned_finished']
                else:
                    if rec.production_id.date_planned_finished < vals['date_planned_finished']:
                        rec.production_id.date_planned_finished = vals['date_planned_finished']

            # Sync end dates with previous work order end dates and production start date
            if 'date_planned_start' in vals:
                if rec.previous_workorder_ids:
                    if rec.previous_workorder_ids[0].date_planned_finished > vals['date_planned_start']:
                        rec.previous_workorder_ids[0].date_planned_finished = vals['date_planned_start']
                else:
                    if rec.production_id.date_planned_start > vals['date_planned_start']:
                        rec.production_id.date_planned_start = vals['date_planned_start']

        # Check that are date_planned_start and date_planned_finished are compatible with the expected duration
        self._check_dates_duration()
        return res


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    def schedule_working_hours(self, nb_hours, date):
        """Returns the datetime that is nb_hours working hours after date in the context of this workcenter."""
        self.ensure_one()
        assert isinstance(date, datetime), u"date should be a datetime.datime. Received %s" % type(date)
        calendar = self.calendar_id
        if not calendar:
            calendar = self.company_id.calendar_id
        if not calendar:
            raise exceptions.UserError(u"You must define a calendar for this workcenter (%s) or this company to "
                                       u"schedule production work orders." % self.name)
        return calendar.schedule_hours_get_date(nb_hours, date, compute_leaves=True)
