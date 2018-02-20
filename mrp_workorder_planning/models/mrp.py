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

from odoo import models, api, exceptions, fields, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.multi
    def write(self, vals):
        for rec in self:
            if not rec.workorder_ids:
                continue
            if 'date_planned_finished' in vals:
                wo_dates = [w.date_planned_finished for w in rec.workorder_ids if w.date_planned_finished]
                if wo_dates and vals['date_planned_finished'] < max(wo_dates):
                    raise exceptions.UserError(_(u"You cannot set the planned end date of a production order before "
                                                 u"the latest end date of its work orders."))
            if 'date_planned_start' in vals:
                wo_dates = [w.date_planned_start for w in rec.workorder_ids if w.date_planned_start]
                if wo_dates and vals['date_planned_start'] > min(wo_dates):
                    raise exceptions.UserError(_(u"You cannot set the planned start date of a production order after "
                                                 u"the earliest start date of its work orders."))
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
            dt_end = fields.Datetime.from_string(date_end)
            current = workorder
            while current:
                dt_end = current.workcenter_id.schedule_working_hours(0, dt_end, zero_backwards=True)
                current.date_planned_finished = dt_end
                dt_start = current.workcenter_id.schedule_working_hours(-current._compute_duration(), dt_end)
                current.date_planned_start = dt_start
                dt_end = dt_start
                current = current.previous_workorder_ids and current.previous_workorder_ids[0] or False


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    previous_workorder_ids = fields.One2many('mrp.workorder', 'next_work_order_id', u"Previous Work Order(s)")

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, "%s - %s" % (rec.production_id.name, rec.name)))
        return res

    def _compute_duration(self):
        res = max(self.duration_expected / 60.0, self.workcenter_id.min_wo_duration)
        return res

    @api.multi
    def button_done(self):
        for rec in self:
            rec.write({
                'date_planned_start': rec.date_start,
                'date_planned_finished': fields.Datetime.now(),
            })
        return super(MrpWorkorder, self).button_done()

    @api.multi
    def write(self, vals):
        for rec in self:
            if 'date_planned_start' in vals:
                if rec.previous_workorder_ids:
                    if rec.previous_workorder_ids[0].date_planned_finished > vals['date_planned_start']:
                        raise exceptions.UserError(_(u"You cannot plan this work order before the previous one: %s") %
                                                   rec.previous_workorder_ids[0].name)
                else:
                    if rec.production_id.date_planned_start > vals['date_planned_start']:
                        rec.production_id.date_planned_start = vals['date_planned_start']
                dps = fields.Datetime.from_string(vals['date_planned_start'])
                dpf = rec.workcenter_id.schedule_working_hours(rec._compute_duration(), dps)
                vals['date_planned_finished'] = fields.Datetime.to_string(dpf)

            if 'date_planned_finished' in vals:
                if rec.next_work_order_id:
                    if rec.next_work_order_id.date_planned_start < vals['date_planned_finished']:
                        raise exceptions.UserError(_(u"You cannot plan this work order after the next one: %s") %
                                                   rec.next_work_order_id.display_name)
                else:
                    if rec.production_id.date_planned_finished < vals['date_planned_finished']:
                        rec.production_id.date_planned_finished = vals['date_planned_finished']
        res = super(MrpWorkorder, self).write(vals)
        return res


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    min_wo_duration = fields.Float(u"Min duration of a workorder (h)")

    def schedule_working_hours(self, nb_hours, date, zero_backwards=False):
        """Returns the datetime that is nb_hours working hours after date in the context of this workcenter."""
        self.ensure_one()
        assert isinstance(date, datetime), _(u"date should be a datetime.datime. Received %s") % type(date)
        calendar = self.calendar_id
        if not calendar:
            calendar = self.company_id.calendar_id
        if not calendar:
            raise exceptions.UserError(_(u"You must define a calendar for this workcenter (%s) or this company to "
                                         u"schedule production work orders.") % self.name)

        available_intervals = calendar.schedule_hours(nb_hours, date, compute_leaves=True)
        target_date = None
        if nb_hours == 0:
            if zero_backwards:
                prev_date = self.schedule_working_hours(-1, date)
                target_date = self.schedule_working_hours(1, prev_date)
            else:
                target_date = available_intervals[-1][1]
        elif nb_hours > 0:
            if available_intervals[-1][0] == available_intervals[-1][1]:
                available_intervals = available_intervals[:-1]
            target_date = available_intervals[-1][1]
        else:
            if available_intervals[0][0] == available_intervals[0][1]:
                available_intervals = available_intervals[1:]
            target_date = available_intervals[0][0]
        return target_date
