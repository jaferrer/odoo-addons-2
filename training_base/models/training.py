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

from odoo import models, fields


class TrainingPartner(models.Model):
    _inherit = 'res.partner'

    is_attendee = fields.Boolean("Is an attendee")
    is_trainer = fields.Boolean("Is a trainer")
    is_institution = fields.Boolean("Is an institution")
    is_training_location = fields.Boolean("Is a training location")


class TrainingTraining(models.Model):
    _name = 'training.training'
    _description = "Training"
    _inherit = 'mail.thread'

    def _get_default_user_id(self):
        return self.env.user

    name = fields.Char(string="Title", required=True)
    user_id = fields.Many2one('res.users', string="Responsible", required=True, default=_get_default_user_id)
    duration = fields.Float(string="Duration (days)")
    price = fields.Float(string="Price")
    aimed_public = fields.Char(string="Aimed Public")
    description = fields.Text(string="Description")
    session_ids = fields.One2many('training.session', 'training_id', string="Sessions")
    sitting_ids = fields.One2many('training.sitting', 'training_id', string="Sittings", readonly=True)


class TrainingSession(models.Model):
    _name = 'training.session'
    _description = "Training session"
    _inherit = 'mail.thread'

    name = fields.Char(string="Title", required=True)
    training_id = fields.Many2one('training.training', string="Training", required=True)
    trainer_id = fields.Many2one('res.partner', string="Trainer", domain=[('is_trainer', '=', True)])
    attendee_ids = fields.Many2many('res.partner', string="Attendees", domain=[('is_attendee', '=', True)])
    location_id = fields.Many2one('res.partner', domain=[('is_training_location', '=', True)], string="Location")
    price = fields.Float(string="Price")


class TrainingSitting(models.Model):
    _name = 'training.sitting'
    _description = "Training sitting"
    _inherit = 'mail.thread'

    session_id = fields.Many2one('training.session', string="Session", required=True)
    training_id = fields.Many2one('training.training', string="Training", related='session_id.training_id',
                                  readonly=True, store=True)
    trainer_id = fields.Many2one('res.partner', string="Trainer", related='session_id.trainer_id',
                                 readonly=True, store=True)
    location_id = fields.Many2one('res.partner', string="Location", related='session_id.location_id',
                                  readonly=True, store=True)
    date = fields.Date(string="Date")
    start_hour = fields.Float(string="Start Hour")
    end_hour = fields.Float(string="End Hour")
