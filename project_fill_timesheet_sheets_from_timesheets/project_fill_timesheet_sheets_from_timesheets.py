# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from dateutil.relativedelta import relativedelta

from odoo import fields, models, api


class TimesheetAutoFill(models.Model):
    _inherit = 'account.analytic.line'

    def get_date_from_for_new_timesheet(self, date, user_id):
        user = self.env['res.users'].browse(user_id)
        range = user.company_id and user.company_id.timesheet_range or 'month'
        if range == 'month':
            return (fields.Date.from_string(date) + relativedelta(day=1)).strftime('%Y-%m-%d')
        elif range == 'week':
            return (fields.Date.from_string(date) + relativedelta(weekday=0, days=-6)).strftime('%Y-%m-%d')
        elif range == 'year':
            return (fields.Date.from_string(date) + relativedelta(day=1, month=1)).strftime('%Y-%m-%d')
        return date

    def get_date_to_for_new_timesheet(self, date, user_id):
        user = self.env['res.users'].browse(user_id)
        range = user.company_id and user.company_id.timesheet_range or 'month'
        if range == 'month':
            return (fields.Date.from_string(date) + relativedelta(months=+1, day=1, days=-1)).strftime('%Y-%m-%d')
        elif range == 'week':
            return (fields.Date.from_string(date) + relativedelta(weekday=6)).strftime('%Y-%m-%d')
        elif range == 'year':
            return (fields.Date.from_string(date) + relativedelta(day=31, month=12)).strftime('%Y-%m-%d')
        return date

    @api.model
    def create_timesheet_if_needed(self, date, user_id):
        employee = self.env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
        user = self.env['res.users'].browse(user_id)
        if not employee and not user.share:
            employee = self.env['hr.employee'].create({
                'user_id': user_id,
                'name': user.name
            })
        if date and not self.env['hr_timesheet_sheet.sheet'].search(
                [('date_to', '>=', date), ('date_from', '<=', date),
                 ('employee_id.user_id.id', '=', user_id),
                 ('state', 'in', ['draft', 'new'])]):
            data = {
                'date_from': self.get_date_from_for_new_timesheet(date, user_id),
                'date_to': self.get_date_to_for_new_timesheet(date, user_id),
                'employee_id': employee.id,
                'department_id': employee.department_id.id,
            }
            self.env['hr_timesheet_sheet.sheet'].create(data)

    @api.model
    def create(self, vals):
        if vals.get('project_id'):
            self.create_timesheet_if_needed(vals.get('date', fields.Date.today()), vals.get('user_id'))
        return super(TimesheetAutoFill, self).create(vals)

    @api.multi
    def write(self, vals):
        for rec in self:
            if vals.get('project_id', rec.project_id):
                self.create_timesheet_if_needed(vals.get('date', rec.date), vals.get('user_id', rec.user_id.id))
        return super(TimesheetAutoFill, self).write(vals)
