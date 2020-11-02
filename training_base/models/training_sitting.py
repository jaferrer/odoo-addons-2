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

from odoo.tools import format_duration

from odoo import models, fields


class TrainingSitting(models.Model):
    _name = 'training.sitting'
    _description = "Training sitting"
    _inherit = 'mail.thread'

    def _get_default_company_id(self):
        return self.env.user.company_id

    session_id = fields.Many2one('training.session', string="Session", required=True, ondelete='cascade')
    training_id = fields.Many2one('training.training', string="Training", related='session_id.training_id',
                                  readonly=True, store=True)
    trainer_id = fields.Many2one('res.partner', string="Trainer", related='session_id.trainer_id',
                                 readonly=True, store=True)
    location_id = fields.Many2one('res.partner', string="Location", related='session_id.location_id',
                                  readonly=True, store=True)
    date = fields.Date(string="Date", required=True)
    start_hour = fields.Float(string="Start Hour", required=True)
    end_hour = fields.Float(string="End Hour", required=True)
    formatted_start_hour = fields.Char(string="Formated Start Hour", compute='_compute_formatted_hours')
    formatted_end_hour = fields.Char(string="Formated End Hour", compute='_compute_formatted_hours')
    attendee_ids = fields.Many2many('res.partner', related='session_id.attendee_ids')
    company_id = fields.Many2one('res.company', string="Company", required=True, default=_get_default_company_id)

    def name_get(self):
        return [(rec.id, "%s (date %s)" % (rec.session_id.display_name, rec.date)) for rec in self]

    def _compute_formatted_hours(self):
        for rec in self:
            rec.formatted_start_hour = format_duration(rec.start_hour)
            rec.formatted_end_hour = format_duration(rec.end_hour)

    def send_convocation_to_all(self):
        for rec in self:
            print(rec)
            for attendee in rec.attendee_ids:
                context_wizard = attendee.with_context(sitting_id=rec.id).send_mail_convocation(
                    return_action_wizard=False)
                wizard = self.env['mail.compose.message'].with_context(context_wizard).create({})
                wizard.write(wizard.onchange_template_id(context_wizard['default_template_id'],
                                                         'comment', self._name, rec.id).get('value'))
                wizard.action_send_mail()


class TrainingAttendee(models.Model):
    _name = 'training.attendee'
    _description = "Training attendee"

    partner_id = fields.Many2one('res.partner', string="Attendee", required=True, ondelete='cascade')
    sitting_id = fields.Many2one('training.sitting', string="Sitting", required=True, ondelete='cascade')
    attendance = fields.Boolean(string="Attendance")

    _sql_constraints = [
        ('unique_attendee', 'unique (partner_id, sitting_id)', "Forbidden to define two attendances for the same "
                                                               "sitting and the same partner.")
    ]


class TrainingSittingConvocationSent(models.Model):
    _name = 'training.sitting.convocation.sent'
    _description = "Convocation sent for sitting"

    partner_id = fields.Many2one('res.partner', string="Attendee", required=True, ondelete='cascade')
    sitting_id = fields.Many2one('training.sitting', string="Sitting", required=True, ondelete='cascade')

    _sql_constraints = [
        ('unique_attendee', 'unique (partner_id, sitting_id)', "Forbidden to define two lines for the same "
                                                               "sitting and the same partner.")
    ]

    def create_line_if_needed(self, partner_id, sitting_id):
        if not self.search([('partner_id', '=', partner_id), ('sitting_id', '=', sitting_id)]):
            self.create({
                'partner_id': partner_id,
                'sitting_id': sitting_id,
            })
