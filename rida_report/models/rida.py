# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import fields, models, api


class RidaReport(models.Model):
    _name = 'rida.report'

    def _get_default_user_ids(self):
        return [(6, 0, [self.env.uid])]

    name = fields.Char(u"Label", required=True)
    code = fields.Char(u"Code", default=lambda self: self.env['ir.sequence'].next_by_code('rida.report'), readonly=True)
    active = fields.Boolean(u"Active", default=True)
    theme_id = fields.Many2one('res.partner', u"Theme", index=True)
    project_id = fields.Many2one('project.project', u"Related project", index=True)
    creation_date = fields.Date(u"Creation date", required=True, default=fields.Date.today)
    line_ids = fields.One2many('rida.line', 'report_id', u"Lines")
    auth_mode = fields.Selection([('public', u"Tout le monde"), ('private', u"Les utilisateurs invités")],
                                 string=u"Utilisateurs autorisés", required=True, default='private')
    user_ids = fields.Many2many('res.users', string=u"Utilisateurs invités", default=_get_default_user_ids)
    state = fields.Selection([
        ('open', u"Open"),
        ('archived', u"Archived"),
    ], u"Status", compute='_compute_state', inverse='_inverse_state')
    line_cpt = fields.Integer(default=0)

    @api.multi
    def _compute_state(self):
        for rec in self:
            rec.state = 'open' if rec.active else 'archived'

    @api.multi
    def _inverse_state(self):
        for rec in self:
            if rec.state == 'open':
                rec.active = True
            elif rec.state == 'archived':
                rec.active = False

    @api.multi
    def name_get(self):
        return [(rec.id, "%s - %s" % (rec.code, rec.name)) for rec in self]


class RidaLine(models.Model):
    _name = 'rida.line'

    type = fields.Selection([
        ('information', u"Information"),
        ('decision', u"Decision"),
        ('action', u"Action")
    ], u"Type", required=True)
    name = fields.Char(u"Description", required=True)
    reference = fields.Char(u"Action reference", readonly=True)
    user_id = fields.Many2one('res.users', u"Related user")
    date = fields.Date(u"Expected date")
    report_id = fields.Many2one('rida.report', u"Related RIDA", required=True, ondelete='cascade')
    project_id = fields.Many2one('project.project', related='report_id.project_id', store=True)
    theme_id = fields.Many2one('res.partner', related='report_id.theme_id', store=True)
    context = fields.Char(u"Context")
    level = fields.Char(u"Level")
    comment = fields.Text(u"Comment")
    date_done = fields.Date(u"Completion date")
    attachment_ids = fields.Many2many('ir.attachment', string=u"Attachments")
    state = fields.Selection([
        ('open', u"Open"),
        ('info', u"Information"),
        ('done', u"Done"),
        ('closed', u"Closed"),
        ('duplicate', u"Duplicate"),
        ('cancel', u"Cancelled")
    ], u"Line state", default='open', required=True)
    priority = fields.Selection([
        ('low', u"Low"),
        ('medium', u"Medium"),
        ('high', u"High"),
    ], u"Priority", default='low')

    @api.onchange('type')
    def onchange_type(self):
        if not self.type:
            self.state = 'open'
            self.priority = False
        elif self.type == 'action':
            self.state = 'open'
            self.priority = 'low'
        else:
            self.state = 'info'
            self.priority = False

    @api.model
    def create(self, vals):
        rida = self.env['rida.report'].browse(vals['report_id'])
        rida.line_cpt += 1
        vals['reference'] = u"%s - %d" % (rida.code, rida.line_cpt)

        if vals.get('state', '') == 'done' and 'date_done' not in vals:
            vals['date_done'] = fields.Date.today()

        return super(RidaLine, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('state', '') == 'done' and 'date_done' not in vals:
            self.filtered(lambda r: not(r.state == 'done' or r.date_done)).write({'date_done': fields.Date.today()})

        return super(RidaLine, self).write(vals)

    @api.multi
    def action_form_view(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rida.line',
            'view_mode': 'form',
            'target': 'current',
            'res_id': self.id,
        }

    @api.multi
    def name_get(self):
        return [(rec.id, rec.reference) for rec in self]
