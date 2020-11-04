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


class TrainingTraining(models.Model):
    _name = 'training.training'
    _description = "Training"
    _inherit = 'mail.thread'

    def _get_default_user_id(self):
        return self.env.user

    def _get_default_company_id(self):
        return self.env.user.company_id

    name = fields.Char(string="Title", required=True, track_visibility='onchange')
    user_id = fields.Many2one('res.users', string="Responsible", required=True, default=_get_default_user_id)
    duration = fields.Float(string="Duration (days)")
    duration_hour_day = fields.Float(string="Duration of one day (in hours)")
    total_duration = fields.Float(string="Total duration (in hours)", compute="_compute_total_duration")
    price = fields.Float(string="Price")
    aimed_public = fields.Char(string="Aimed Public")
    description = fields.Text(string="Description")
    training_content = fields.Text(string="Content of training")
    session_ids = fields.One2many('training.session', 'training_id', string="Sessions")
    sitting_ids = fields.One2many('training.sitting', 'training_id', string="Sittings", readonly=True)
    next_session = fields.Many2one('training.session', compute='_compute_next_session')
    nb_mini = fields.Integer("Minimum number of attendees")
    nb_maxi = fields.Integer("Maximum number of attendees")
    state = fields.Selection([('draft', "Draft"),
                              ('validated', "Validated"),
                              ('active', "Active"),
                              ('cancel', "Cancelled"),
                              ('done', "Done")], strong="Status", default='draft', required=True,
                             track_visibility='onchange')
    company_id = fields.Many2one('res.company', string="Company", required=True, default=_get_default_company_id)

    @api.depends('duration', 'duration_hour_day')
    def _compute_total_duration(self):
        for rec in self:
            rec.total_duration = rec.duration * rec.duration_hour_day

    @api.depends('session_ids')
    def _compute_next_session(self):
        for rec in self:
            session = self.env['training.session'].search([
                ('state', 'in', ('offered', 'registrations')),
                ('training_id', '=', rec.id)
            ], limit=1)
            rec.next_session = session
