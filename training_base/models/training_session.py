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

from odoo import models, fields, api


class TrainingSession(models.Model):
    _name = 'training.session'
    _description = "Training session"
    _inherit = 'mail.thread'

    def _get_default_company_id(self):
        return self.env.user.company_id

    def _get_default_trainer_id(self):
        return self.env.user.partner_id.is_trainer and self.env.user.partner_id or False

    training_id = fields.Many2one('training.training', string="Training", required=True, ondelete='cascade')
    trainer_id = fields.Many2one('res.partner', string="Trainer", domain=[('is_trainer', '=', True)],
                                 default=_get_default_trainer_id)
    attendee_ids = fields.Many2many('res.partner', string="Attendees", domain=[('is_attendee', '=', True)])
    nb_attendees = fields.Integer(string="Number of attendees", compute='_compute_nb_attendees', store=True)
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
    company_id = fields.Many2one('res.company', string="Company", required=True, default=_get_default_company_id)

    def name_get(self):
        result = []
        for rec in self:
            ordered_sessions = self.search([('id', 'in', rec.training_id.session_ids.ids)],
                                           order='first_sitting_date, id')
            nb_sessions_for_training = len(ordered_sessions)
            session_index = 0
            for session in ordered_sessions:
                session_index += 1
                if session == rec:
                    break
            result += [(rec.id, "%s (%s/%s)" % (rec.training_id.name, session_index, nb_sessions_for_training))]
        return result

    @api.onchange('training_id')
    def onchange_training_id(self):
        if self.training_id and self.training_id.nb_mini:
            self.nb_mini = self.training_id.nb_mini
        if self.training_id and self.training_id.nb_maxi:
            self.nb_maxi = self.training_id.nb_maxi
        if self.training_id:
            self.price = self.training_id.price

    @api.depends('attendee_ids')
    def _compute_nb_attendees(self):
        for rec in self:
            rec.nb_attendees = len(rec.attendee_ids)

    @api.depends('sitting_ids', 'sitting_ids.date')
    def _compute_sitting_dates(self):
        for rec in self:
            sittings = self.env['training.sitting'].search([('id', 'in', rec.sitting_ids.ids)], order='date')
            rec.first_sitting_date = sittings and sittings[0].date or False
            rec.last_sitting_date = sittings and sittings[-1].date or False
