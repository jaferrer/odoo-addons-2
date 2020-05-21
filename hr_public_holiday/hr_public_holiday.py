# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
import datetime
from urllib2 import urlopen
import json
from odoo import models, fields, api
from odoo.exceptions import UserError


class PublicHoliday(models.Model):
    _name = 'ndp.public.holiday'
    _description = u"Jours fériés"
    _order = 'date'

    date = fields.Datetime(u"Date", required=True)
    name = fields.Char(u"Nom", required=True)
    area = fields.Char(u"Zone", required=True, default='metropole')
    year = fields.Char(u"Année", required=True, default=str(datetime.date.today().year))
    holiday_status_id = fields.Many2one('hr.holidays.status', u"Type de congé",
                                        default=lambda self: self.env.ref('hr_public_holiday.holiday_status_public'))

    @api.multi
    def update_public_holidays(self):
        self.env['ndp.public.holiday'].search([]).unlink()
        area, year = 'metropole', datetime.date.today().year
        url = u"https://etalab.github.io/jours-feries-france-api/{zone}/{annee}.json".format(zone=area, annee=year)
        response = urlopen(url)
        public_holidays = json.loads(response.read().decode('utf-8'))

        for key, value in public_holidays.items():
            date = datetime.datetime.strptime(key, '%Y-%m-%d')
            date = datetime.date(date.year, date.month, date.day)
            if date >= datetime.date.today():
                self.env['ndp.public.holiday'].create({'date': date, 'name': value, 'area': area, 'year': str(year)})

    @api.multi
    def update_employees_public_holidays(self):
        self.update_public_holidays()
        employees = self.env['hr.employee'].search([])
        public_holidays = self.env['ndp.public.holiday'].search([])

        for employee in employees:
            for public_holiday in public_holidays:
                if not self.env['hr.holidays'].search([('date_start', '=', public_holiday.date),
                                                       ('employee_id', '=', employee.id), ]):
                    try:
                        self.env['hr.holidays'].create({'employee_id': employee.id,
                                                        'name': public_holiday.name,
                                                        'date_start': public_holiday.date,
                                                        'holiday_status_id': public_holiday.holiday_status_id.id, })
                    except Exception:
                        raise UserError(
                            u"{} a un déjà un congé pendant le {} à la date du {}".format(
                                employee.name, public_holiday.name, public_holiday.date)
                        )
