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
#    MERCHANTABILITY or FITNESS FOR Odoo server error à l'utilisation d'un compteA PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from datetime import timedelta, date

from odoo import models, fields, api, _


class TimesheetReminderHrEmployee(models.Model):
    _inherit = 'hr.employee'

    timesheet_sheet_required = fields.Boolean(u"Timesheets required", default=True)

    @api.multi
    def get_timesheet_between_dates(self, date_from, date_to):
        self.ensure_one()
        return self.env['hr_timesheet_sheet.sheet']. \
            search([('employee_id', '=', self.id),
                    ('date_from', '>=', date_from),
                    ('date_to', '<', date_to)])

    @api.multi
    def get_first_timesheet(self):
        self.ensure_one()
        return self.env['hr_timesheet_sheet.sheet'].search([('employee_id', '=', self.id)],
                                                           order='date_from asc', limit=1)

    @api.multi
    def check_timesheet_last_week(self, date_from, date_to):
        self.ensure_one()
        message = u""""""
        timesheet_last_week = self.get_timesheet_between_dates(date_from, date_to)
        if not timesheet_last_week:
            message += _(u"""No timesheet found for week from %s to %s.""") % (date_from, date_to)
        elif timesheet_last_week.state in ['new', 'draft']:
            message += _(u"""Please validate your timesheet for week from %s to %s.""") % (date_from, date_to)
        return message

    @api.multi
    def check_timesheet_blanks(self, message, date_last_monday):
        self.ensure_one()
        first_timesheet = self.get_first_timesheet()
        if not first_timesheet:
            return message
        first_date_from = fields.Date.from_string(first_timesheet.date_from)
        cursor_monday = first_date_from + timedelta(days=-first_date_from.weekday())
        cursor_next_monday = cursor_monday + timedelta(weeks=1)
        blanks_list = []
        while cursor_next_monday < date_last_monday:
            cursor_monday += timedelta(weeks=1)
            cursor_next_monday += timedelta(weeks=1)
            timesheet = self.get_timesheet_between_dates(cursor_monday, cursor_next_monday)
            if not timesheet or timesheet.state in ['new', 'draft']:
                blanks_list += [(cursor_monday, cursor_next_monday)]
        if blanks_list:
            if message:
                message += u"""\n\n"""
            message += _(u"""List of missing or non-confirmed timesheets in history:""")
            for blank in blanks_list:
                message += u"""\n - """
                message += _(u"""Week from %s to %s""") % (fields.Date.to_string(blank[0]),
                                                           fields.Date.to_string(blank[1]))
        return message

    @api.model
    def cron_send_timesheets_reminder(self):
        date_today_dt = date.today()
        date_monday_dt = date_today_dt + timedelta(days=-date_today_dt.weekday())
        date_previous_monday_dt = date_monday_dt + timedelta(weeks=-1)
        date_monday_string = fields.Date.to_string(date_monday_dt)
        date_previous_monday_string = fields.Date.to_string(date_previous_monday_dt)
        for employee in self.search([('timesheet_sheet_required', '=', True)]):
            message = employee.check_timesheet_last_week(date_previous_monday_string, date_monday_string)
            message = employee.check_timesheet_blanks(message, date_monday_dt)
            if message:
                message = u"""\n\n""".join([_(u"""Dear %s,""") % employee.name,
                                            message, _(u"""Best regards,"""),
                                            self.env.user.name])
                values = {
                    'model': None,
                    'res_id': None,
                    'subject': _(u"Update your timesheets"),
                    'body': message,
                    'body_html': message.replace(u"\n", u"<br>"),
                    'parent_id': None,
                    'email_from': self.env.user.email or None,
                    'auto_delete': False,
                    'email_to': employee.work_email
                }
                self.env['mail.mail'].create(values).send()
