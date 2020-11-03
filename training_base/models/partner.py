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

from odoo import models, fields, exceptions, api, _


class TrainingPartner(models.Model):
    _inherit = 'res.partner'

    is_attendee = fields.Boolean("Is an attendee")
    is_trainer = fields.Boolean("Is a trainer")
    is_institution = fields.Boolean("Is an institution")
    is_training_location = fields.Boolean("Is a training location")
    attendance = fields.Selection([('normal', "Attendance not known"),
                                   ('blocked', "No attendance"),
                                   ('done', "Attendance")], string="Attendance", compute='_compute_attendance')
    convocation_sent = fields.Boolean(string="Convocation sent", compute='_compute_convocation_sent')
    convocation_sent_ids = fields.One2many('training.sitting.convocation.sent', 'partner_id')
    biography = fields.Text("Biography")

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

    @api.onchange('is_institution')
    def onchange_is_institution(self):
        print('onchange_is_institution', self)
        if self.is_institution:
            self.is_company = True

    @api.onchange('is_training_location')
    def onchange_is_training_location(self):
        if self.is_training_location:
            self.is_company = True

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

    def send_mail_convocation(self, return_action_wizard=True):
        self.ensure_one()
        sitting_id = self.env.context.get('sitting_id', 0)
        if not sitting_id:
            raise exceptions.UserError(_("Impossible to send a convocation with no sitting provided"))
        sitting = self.env['training.sitting'].browse(sitting_id)
        if not sitting.location_id:
            raise exceptions.UserError(_("Impossible to send a convocation with no sitting location provided"))
        if not sitting.location_id.street or not sitting.location_id.zip or not sitting.location_id.city:
            raise exceptions.UserError(_("Impossible to send a convocation with no sitting location adress provided"))
        template = self.env.ref('training_base.email_template_training_convocation_to_partner')
        ctx = {
            'partner_to': self.id,
            'default_res_id': sitting.id,
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'lang': self.lang or self.env.user.lang,
            'send_mail_convocation': (self.id, sitting_id),
        }
        if return_action_wizard:
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(False, 'form')],
                'view_id': False,
                'target': 'new',
                'context': ctx,
            }
        return ctx

    def mark_convocation_as_not_sent(self):
        self.ensure_one()
        sitting_id = self.env.context.get('sitting_id', 0)
        if not sitting_id:
            raise exceptions.UserError(_("Impossible action with no sitting provided"))
        self.env['training.sitting.convocation.sent'].search([('partner_id', '=', self.id),
                                                              ('sitting_id', '=', sitting_id)]).unlink()
