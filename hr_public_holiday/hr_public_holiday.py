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
import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PublicHoliday(models.Model):
    _name = 'hr.public.holiday'
    _description = u"Jours fériés"
    _order = 'date'

    date = fields.Datetime(u"Date", required=True)
    name = fields.Char(u"Nom", required=True)
    area = fields.Char(u"Zone", required=True, default='metropole')
    year = fields.Char(u"Année", required=True, default=str(datetime.date.today().year))

    @api.model
    def download_public_holidays(self):
        self.search([]).unlink()
        area = 'metropole'
        year = datetime.date.today().year
        url = u"https://etalab.github.io/jours-feries-france-api/{zone}/{annee}.json".format(zone=area, annee=year)
        response = urlopen(url)
        public_holidays = json.loads(response.read().decode('utf-8'))

        for key, value in public_holidays.items():
            date = datetime.datetime.strptime(key, '%Y-%m-%d')
            date = datetime.date(date.year, date.month, date.day)
            if date >= datetime.date.today():
                self.create({'date': date, 'name': value, 'area': area, 'year': str(year)})


class HrPublicHolidayCreate(models.TransientModel):
    _name = 'hr.public.holiday.create'

    def _get_year(self):
        years = set(self.env['hr.public.holiday'].search([]).mapped('year'))
        return [(y, y) for y in sorted(list(years))]

    holiday_status_id = fields.Many2one('hr.holidays.status', u"Type de congé")
    employee_ids = fields.Many2many('hr.employee', string=u"Employés")
    department_ids = fields.Many2many('hr.department', string=u"Départements")
    by_type = fields.Selection([('employee', u"Employé"), ('department', u"Département")], u"Pour")
    auto_confirm_holiday = fields.Boolean(u"Confirmer les congés automatiquement")
    mode = fields.Selection([('add', u"Ajouter"), ('refuse', u"Annuler")], u"Mode")
    delete_refuse = fields.Boolean(u"Supprimer les congés une fois annulés")
    year = fields.Selection('_get_year', u"Pour l'année", required=True)

    @api.multi
    def create_holydays(self):
        self.ensure_one()
        employees = self.employee_ids
        if self.by_type == 'department':
            deps = self.env['hr.department'].search([('id', 'child_of', self.department_ids.ids)])
            employees = self.env['hr.employee'].search([('department_id', 'in', deps.ids)])
        public_holidays = self.env['hr.public.holiday'].search([('year', '=', self.year)])
        if self.mode == 'add':
            for employee in employees:
                for public_holiday in public_holidays:
                    try:
                        holiday = self.env['hr.holidays'].create({
                            'employee_id': employee.id,
                            'name': public_holiday.name,
                            'date_start': public_holiday.date,
                            'holiday_status_id': self.holiday_status_id.id,
                        })
                        holiday.action_approve()
                    except ValidationError:
                        _logger.info(u"%s a un déjà un congé pendant le %s à la date du %s",
                                     employee.name, public_holiday.name, public_holiday.date
                                     )
        else:
            for public_holiday in public_holidays:
                holiday = self.env['hr.holidays'].search([
                    ('employee_id', 'in', employees.ids), ('date_start', '=', public_holiday.date)]
                )
                if holiday.state not in ['draft', 'cancel', 'confirm']:
                    holiday.action_refuse()
                holiday.action_draft()
                if self.delete_refuse:
                    holiday.unlink()
