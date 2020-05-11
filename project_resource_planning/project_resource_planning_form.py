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


class IrUIView(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[VIEW])


class ProjectProject(models.Model):
    _inherit = 'project.project'

    used_in_resource_planning = fields.Boolean(u"Used In Resource Planning", default=True)
    color_code = fields.Char(u"Color Code", default="#d72571")


class ProjectResourcePlanningSheet(models.Model):
    _name = 'resource.planning.cell'
    _description = u"Resource Planning"
    _order = 'department_id, employee_id, date_start'

    @api.multi
    def name_get(self):
        grp_on = self.env.context.get('grouped_on', 'employee_id')
        if grp_on == 'employee_id':
            return [(rec.id, rec.project_id.name) for rec in self]
        elif grp_on == 'project_id':
            return [(rec.id, rec.employee_id.name) for rec in self]
        return [(rec.id, u"%s - %s" % (rec.employee_id.name, rec.project_id.name)) for rec in self]

    employee_id = fields.Many2one('hr.employee', u"Employé", required=True)
    department_id = fields.Many2one('hr.department', u"Départnement", readonly=True,
                                    related='employee_id.department_id', store=True)
    project_color = fields.Char(u"Color Code", related='project_id.color_code', store=True)
    datetime_start = fields.Datetime(u"Start Datetime", required=True)
    datetime_end = fields.Datetime(u"End Datetime", required=True)
    project_id = fields.Many2one('project.project', u"Project", domain=[('used_in_resource_planning', '=', True)],
                                 required=True)
    overlap = fields.Boolean(u"Overlap", compute='_compute_overlap')
    date_start = fields.Date(u"Start Date")
    date_end = fields.Date(u"End Date")
    period_start = fields.Selection(PERIOD, u"Period Start")
    period_end = fields.Selection(PERIOD, u"Period End")

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        new_order = orderby or self._order
        return super(ProjectResourcePlanningSheet, self).read_group(
            domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=new_order, lazy=lazy)

    @api.multi
    @api.onchange('datetime_start', 'datetime_end')
    def _onchange_date_real(self):
        for rec in self:
            dt_start = FR_STR(rec.datetime_start)
            dt_end = FR_STR(rec.datetime_end)
            rec.period_end = dt_end.hour == 0 and "pm" or "am"
            rec.date_end = rec.period_end == 'pm' and dt_end.date() + relativedelta(seconds=-1) or dt_end.date()

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
