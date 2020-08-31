# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api

FR_STR = fields.Datetime.from_string
DFR_STR = fields.Date.from_string

VIEW = ('planning', 'Planning')

PERIOD = [
    ('am', u"AM"),
    ('pm', u"PM"),
]

QUERY_EXIST = """SELECT 1
             FROM resource_planning_cell b
             WHERE a.datetime_start < b.datetime_end
               AND a.datetime_end > b.datetime_start
               AND a.%(grouped_on)s = b.%(grouped_on)s
               AND a.id != b.id"""


def _round_time(dt=None, round_to=60):
    """
    https://stackoverflow.com/questions/3463930/how-to-round-the-minute-of-a-datetime-object-python/10854034#10854034
    Round a datetime object to any time lapse in seconds
    dt : datetime.datetime object, default now.
    roundTo : Closest number of seconds to round to, default 1 minute.
    Author: Thierry Husson 2012 - Use it as you want but don't blame me.
    """
    if dt is None:
        dt = datetime.datetime.now()
    seconds = (dt.replace(tzinfo=None) - dt.min).seconds
    rounding = (seconds + round_to / 2) // round_to * round_to
    return dt + datetime.timedelta(0, rounding - seconds, -dt.microsecond)


class IrUIView(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[VIEW])


class ProjectProject(models.Model):
    _inherit = 'project.project'

    planning_name = fields.Char(u"Name display in Planning")
    used_in_resource_planning = fields.Boolean(u"Used In Resource Planning", default=True)
    color_code = fields.Char(u"Color Code", default="#d72571")

    @api.model
    def create(self, vals):
        vals['planning_name'] = vals.get('planning_name', vals['name'])
        return super(ProjectProject, self).create(vals)


class HrHolidays(models.Model):
    """Update analytic lines on status change of Leave Request"""
    _inherit = 'hr.holidays'

    # Timesheet entry linked to this leave request
    planning_cell_ids = fields.One2many('resource.planning.cell', 'leave_id', u"Planning Cells")

    @api.multi
    def action_approve(self):
        res = super(HrHolidays, self).action_approve()
        self._auto_create_planning_cells()
        return res

    @api.multi
    def _auto_create_planning_cells(self):
        for rec in self:
            if rec.type == 'remove' and rec.holiday_status_id.project_id:
                dt_from = fields.Datetime.from_string(rec.date_from)
                dt_to = fields.Datetime.from_string(rec.date_to)
                delta = datetime.timedelta(hours=5, minutes=59)
                dt_from = _round_time(dt_from - delta, 12 * 60 * 60)
                dt_to = _round_time(dt_to + delta, 12 * 60 * 60)
                self.env['resource.planning.cell'].create({
                    'display_type': 'background',
                    'project_id': rec.holiday_status_id.project_id.id,
                    'employee_id': rec.employee_id.id,
                    'datetime_start': dt_from,
                    'datetime_end': dt_to,
                    'leave_id': rec.id,
                })

    @api.multi
    def action_refuse(self):
        res = super(HrHolidays, self).action_refuse()
        self.mapped('planning_cell_ids').unlink()
        return res


class ProjectResourcePlanningSheet(models.Model):
    _name = 'resource.planning.cell'
    _description = u"Resource Planning"
    _order = 'department_id, employee_id, datetime_start'

    @api.multi
    def name_get(self):
        grp_on = self.env.context.get('grouped_on', 'employee_id')
        if grp_on == 'employee_id':
            return [(rec.id, rec.project_id.planning_name or rec.project_id.name) for rec in self]
        elif grp_on == 'project_id':
            return [(rec.id, rec.employee_id.name) for rec in self]
        return [
            (rec.id, u"%s - %s" % (rec.employee_id.name, rec.project_id.planning_name or rec.project_id.name))
            for rec in self
        ]

    leave_id = fields.Many2one('hr.holidays', u"Leave")
    employee_id = fields.Many2one('hr.employee', u"Employee", required=True)
    department_id = fields.Many2one('hr.department', u"Départment", readonly=True,
                                    related='employee_id.department_id', store=True)
    display_type = fields.Selection([('background', u"Fond de couleur"), ('range', u"Bloc")],
                                    u"Format")
    project_color = fields.Char(u"Color Code", related='project_id.color_code', store=True)
    datetime_start = fields.Datetime(u"Start Datetime", required=True, default=fields.Date.today)
    datetime_end = fields.Datetime(u"End Datetime", required=True, default=fields.Date.today)
    project_id = fields.Many2one('project.project', u"Project", domain=[('used_in_resource_planning', '=', True)],
                                 required=True)
    overlap = fields.Boolean(u"Overlap", compute='_compute_overlap')

    date_start = fields.Date(u"Start Date")
    date_end = fields.Date(u"End Date")
    period_start = fields.Selection(PERIOD, u"Period Start")
    period_end = fields.Selection(PERIOD, u"Period End")
    nb_days = fields.Float(u"#Days", compute='_compute_nb_days', store=True)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        new_order = orderby or self._order
        return super(ProjectResourcePlanningSheet, self).read_group(
            domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=new_order, lazy=lazy
        )

    @api.multi
    @api.depends('period_start', 'period_end')
    def _compute_nb_days(self):
        for rec in self:
            dt_start = fields.Datetime.from_string(rec.datetime_start)
            dt_end = fields.Datetime.from_string(rec.datetime_end)
            delta = (dt_end - dt_start)
            rec.nb_days = delta.total_seconds() / 3600 / 24

    @api.model
    def create(self, vals):
        res = super(ProjectResourcePlanningSheet, self).create(vals)
        res.with_context(no_recompute=True)._onchange_date_real()
        return res

    @api.multi
    def write(self, vals):
        res = super(ProjectResourcePlanningSheet, self).write(vals)
        if not self.env.context.get('no_recompute'):
            self.with_context(no_recompute=True)._onchange_date_real()
        return res

    @api.multi
    @api.onchange('datetime_start', 'datetime_end')
    def _onchange_date_real(self):
        for rec in self:
            dt_start = FR_STR(rec.datetime_start)
            dt_end = FR_STR(rec.datetime_end)
            if dt_end :
                rec.period_end = dt_end.hour == 0 and "pm" or "am"
                rec.date_end = rec.period_end == 'pm' and dt_end.date() + relativedelta(seconds=-1) or dt_end.date()
            if dt_start:
                rec.period_start = dt_start.hour == 12 and "pm" or "am"
                rec.date_start = dt_start.date()

    @api.multi
    @api.onchange('date_start', 'period_start', 'date_end', 'period_end')
    def _onchange_date_simple(self):
        for rec in self:
            d_end = DFR_STR(rec.date_end)
            d_start = DFR_STR(rec.date_start)
            if rec.period_end == 'pm':
                rec.datetime_end = datetime.datetime.combine(d_end + relativedelta(days=1), datetime.time(0, 0, 0))
            else:
                rec.datetime_end = datetime.datetime.combine(d_end, datetime.time(12, 0, 0))

            if rec.period_start == 'am':
                rec.datetime_start = datetime.datetime.combine(d_start, datetime.time(0, 0, 0))
            else:
                rec.datetime_start = datetime.datetime.combine(d_start, datetime.time(12, 0, 0))

    @api.multi
    def _compute_overlap(self):
        query = "SELECT id FROM "
        query += self._table
        query += " AS a"
        query += " WHERE id IN %s"
        query += " AND "
        query += "EXISTS("
        query += QUERY_EXIST % {'grouped_on': self.env.context.get('grouped_on', 'employee_id')}
        query += ")"

        self.env.cr.execute(query, (tuple(self.ids),))
        res = [r['id'] for r in self.env.cr.dictfetchall()]
        for rec in self:
            rec.overlap = rec.id in res
