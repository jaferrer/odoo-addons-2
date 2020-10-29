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

from odoo import models, fields, exceptions, api


class TrainingPartner(models.Model):
    _inherit = 'res.partner'

    is_attendee = fields.Boolean("Is an attendee")
    is_trainer = fields.Boolean("Is a trainer")
    is_institution = fields.Boolean("Is an institution")
    is_training_location = fields.Boolean("Is a training location")
    attendance = fields.Selection([('normal', "Attendance not known"),
                                   ('blocked', "No attendance"),
                                   ('done', "Attendance")], string="Attendance", compute='_compute_attendance')

    def _compute_attendance(self):
        sitting_id = self.env.context.get('sitting_id', 0)
        if not sitting_id:
            raise exceptions.UserError("Impossible to determine attendance if no sitting provided")
        for rec in self:
            attendance = self.env['training.attendee'].search([('sitting_id', '=', sitting_id),
                                                               ('partner_id', '=', rec.id)], limit=1)
            if attendance:
                if attendance.attendance:
                    rec.attendance = 'done'
                else:
                    rec.attendance = 'blocked'
            else:
                rec.attendance = 'normal'

    def define_attendance(self, attendance):
        self.ensure_one()
        sitting_id = self.env.context.get('sitting_id', 0)
        if not sitting_id:
            raise exceptions.UserError("Impossible to define attendance if no sitting provided")
        attendee = self.env['training.attendee'].search([('sitting_id', '=', sitting_id),
                                                         ('partner_id', '=', self.id)], limit=1)
        if attendance == 'normal':
            attendee.unlink()
            return
        vals = {
            'sitting_id': sitting_id,
            'partner_id': self.id,
        }
        if attendance == 'blocked':
            vals['attendance'] = False
        if attendance == 'done':
            vals['attendance'] = True
        if attendee:
            attendee.write(vals)
            return
        attendee.create(vals)

    def button_set_attendance(self):
        self.define_attendance('done')

    def button_set_no_attendance(self):
        self.define_attendance('blocked')

    def button_set_attendance_unknown(self):
        self.define_attendance('normal')


class TrainingTraining(models.Model):
    _name = 'training.training'
    _description = "Training"
    _inherit = 'mail.thread'

    def _get_default_user_id(self):
        return self.env.user

    name = fields.Char(string="Title", required=True, track_visibility='onchange')
    user_id = fields.Many2one('res.users', string="Responsible", required=True, default=_get_default_user_id)
    duration = fields.Float(string="Duration (days)")
    price = fields.Float(string="Price")
    aimed_public = fields.Char(string="Aimed Public")
    description = fields.Text(string="Description")
    session_ids = fields.One2many('training.session', 'training_id', string="Sessions")
    sitting_ids = fields.One2many('training.sitting', 'training_id', string="Sittings", readonly=True)
    nb_mini = fields.Integer("Minimum number of attendees")
    nb_maxi = fields.Integer("Maximum number of attendees")
    state = fields.Selection([('draft', "Draft"),
                              ('validated', "Validated"),
                              ('active', "Active"),
                              ('cancel', "Cancelled"),
                              ('done', "Done")], strong="Status", default='draft', required=True,
                             track_visibility='onchange')


class TrainingSession(models.Model):
    _name = 'training.session'
    _description = "Training session"
    _inherit = 'mail.thread'

    name = fields.Char(string="Title", required=True)
    training_id = fields.Many2one('training.training', string="Training", required=True, ondelete='cascade')
    trainer_id = fields.Many2one('res.partner', string="Trainer", domain=[('is_trainer', '=', True)])
    attendee_ids = fields.Many2many('res.partner', string="Attendees", domain=[('is_attendee', '=', True)])
    location_id = fields.Many2one('res.partner', domain=[('is_training_location', '=', True)], string="Location")
    price = fields.Float(string="Price")
    sitting_ids = fields.One2many('training.sitting', 'session_id', string="Sittings")
    nb_mini = fields.Integer("Minimum number of attendees")
    nb_maxi = fields.Integer("Maximum number of attendees")
    first_sitting_date = fields.Date(string="Fist sitting date", compute='_compute_sitting_dates', store=True)
    last_sitting_date = fields.Date(string="Last sitting date", compute='_compute_sitting_dates', store=True)
    state = fields.Selection([('draft', "Draft"),
                              ('offered', "Offered"),
                              ('registrations', "Registrations"),
                              ('ready', "Ready"),
                              ('convocations_sent', "Convocations sent"),
                              ('cancel', "Cancelled"),
                              ('finished', "Finished"),
                              ('done', "Done")], strong="Status", default='draft', required=True,
                             track_visibility='onchange')

    def name_get(self):
        return [(rec.id, "%s / %s" % (rec.training_id.display_name, rec.name)) for rec in self]

    @api.onchange('training_id')
    def onchange_training_id(self):
        if self.training_id and self.training_id.nb_mini:
            self.nb_mini = self.training_id.nb_mini
        if self.training_id and self.training_id.nb_maxi:
            self.nb_maxi = self.training_id.nb_maxi

    @api.depends('sitting_ids', 'sitting_ids.date')
    def _compute_sitting_dates(self):
        for rec in self:
            sittings = self.env['training.sitting'].search([('id', 'in', rec.sitting_ids.ids)], order='date')
            rec.first_sitting_date = sittings and sittings[0].date or False
            rec.last_sitting_date = sittings and sittings[-1].date or False


class TrainingSitting(models.Model):
    _name = 'training.sitting'
    _description = "Training sitting"
    _inherit = 'mail.thread'

    session_id = fields.Many2one('training.session', string="Session", required=True, ondelete='cascade')
    training_id = fields.Many2one('training.training', string="Training", related='session_id.training_id',
                                  readonly=True, store=True)
    trainer_id = fields.Many2one('res.partner', string="Trainer", related='session_id.trainer_id',
                                 readonly=True, store=True)
    location_id = fields.Many2one('res.partner', string="Location", related='session_id.location_id',
                                  readonly=True, store=True)
    date = fields.Date(string="Date")
    start_hour = fields.Float(string="Start Hour")
    end_hour = fields.Float(string="End Hour")
    attendee_ids = fields.Many2many('res.partner', related='session_id.attendee_ids')

    def name_get(self):
        return [(rec.id, "%s (date %s)" % (rec.session_id.display_name, rec.date)) for rec in self]


class TrainingAttendee(models.Model):
    _name = 'training.attendee'
    _description = "Training attendee"

    partner_id = fields.Many2one('res.partner', string="Attendees", required=True, ondelete='cascade')
    sitting_id = fields.Many2one('training.sitting', string="Sitting", required=True, ondelete='cascade')
    attendance = fields.Boolean(string="Attendance")

    _sql_constraints = [
        ('unique_attendee', 'unique (partner_id, sitting_id)', "Forbidden to define two attendances for the same "
                                                               "sitting and the same partner.")
    ]
