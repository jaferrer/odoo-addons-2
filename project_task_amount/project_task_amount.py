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

from datetime import timedelta

from odoo import fields, models, api


class ProjectTask(models.Model):
    _inherit = 'project.task'

    effective_hours = fields.Float(u"Time spent (Hours)")
    effective_days = fields.Float(u"Time spent (Days)", compute='_compute_effective_days')
    remaining_hours = fields.Float(u"Remaining Time")
    planned_hours = fields.Float(u"Tps prévu (Heures)", readonly=True)
    planned_days = fields.Float(u"Tps prévu (Jours)", track_visibility='onchange')

    @api.multi
    def write(self, vals):
        if 'planned_hours' in vals:
            vals['planned_days'] = vals['planned_hours'] / 7
        elif 'planned_days' in vals:
            vals['planned_hours'] = vals['planned_days'] * 7
        return super(ProjectTask, self).write(vals)

    @api.model
    def create(self, vals):
        if 'planned_hours' in vals:
            vals['planned_days'] = vals['planned_hours'] / 7
        elif 'planned_days' in vals:
            vals['planned_hours'] = vals['planned_days'] * 7
        return super(ProjectTask, self).create(vals)

    @api.multi
    def add_line_timesheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'task.timesheet.amount',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self._context, active_id=self.id),
        }

    @api.multi
    def _compute_effective_days(self):
        for rec in self:
            rec.effective_days = rec.effective_hours / 7


class TaskTimeSheetAmount(models.TransientModel):
    _name = 'task.timesheet.amount'

    date = fields.Date(u"Date", default=fields.Date.context_today, required=True)
    comment = fields.Char(u"Additionnal Comment")
    amount_days = fields.Float(u"Temps (Jours)",
                               compute='_compute_amount_days',
                               inverse='_inverse_amount_days')
    amount_hours = fields.Float(u"Temps (Heures)", required=True)
    lissage = fields.Selection(
        [
            ('none', u"Aucun lissage"),
            ('from_date', u"A partir de la date"),
            ('to_date', u"Jusqu'à la date"),
        ],
        u"Lissage",
        required=True,
        default='none'
    )

    @api.multi
    def _inverse_amount_days(self):
        for rec in self:
            if rec.amount_days > 0:
                rec.amount_hours = rec.amount_days * 7

    @api.multi
    def _compute_amount_days(self):
        for rec in self:
            if rec.amount_hours > 0:
                rec.amount_days = rec.amount_hours / 7

    @api.multi
    def create_line(self):
        self.ensure_one()
        amount_left = self.amount_hours
        if self.lissage != 'none':
            while amount_left > 0:
                if self.lissage == 'from_date':
                    days_to_add = (amount_left / 7 - self.amount_hours / 7) * -1
                else:
                    days_to_add = int(amount_left / -7)
                date = fields.Date.from_string(self.date) + timedelta(days=days_to_add)
                amount = amount_left > 7 and 7 or amount_left
                self._create_analytic_line(amount, date)
                amount_left = amount_left - 7
        else:
            self._create_analytic_line(self.amount_hours, self.date)

    def _create_analytic_line(self, amount, date):
        task = self.env['project.task'].browse(self.env.context.get('active_id'))
        self.env['account.analytic.line'].create({
            'project_id': task.project_id.id,
            'task_id': task.id,
            'name': self.comment or "/",
            'user_id': self.env.user.id,
            'date': date,
            'unit_amount': amount
        })
