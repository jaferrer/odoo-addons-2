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

from odoo import fields, models, api, exceptions, _


class ProjectMilestone(models.Model):
    _name = 'project.milestone'

    name = fields.Char(u"Title", required=True)
    active = fields.Boolean(u"Active", default=True, readonly=True)
    project_id = fields.Many2one('project.project', u"Project", required=True)
    task_ids = fields.One2many('project.task', 'milestone_id', u"Task", readonly=True)
    nb_tasks = fields.Integer(u"Nb Task", compute='_compute_nb_related')
    nb_days_tasks = fields.Integer(u"Number of days", compute='_compute_nb_related')
    start_date = fields.Date(u"Start date", required=True)
    qualif_should_be_livred_at = fields.Date(u"Should be in Test at", required=True)
    should_be_closed_at = fields.Date(u"Should be in Prod at")
    should_be_test_before = fields.Date(u"Should be tested before")
    livred_in_qualif_at = fields.Date(u"Delivery in Test at", readonly=True)
    livred_in_qualif_by = fields.Many2one('res.users', u"Delivery in Test by", readonly=True)
    livred_in_prod_at = fields.Date(u"Delivery in Prod at", readonly=True)
    livred_in_prod_by = fields.Many2one('res.users', u"Delivery in Prod by", readonly=True)
    closed_by = fields.Many2one('res.users', u"Closed by", readonly=True)
    closed_at = fields.Date(u"Closed at", readonly=True)
    state = fields.Selection([
        ('open', u"Open"),
        ('in_qualif', u"In Test"),
        ('in_prod', u"In Production"),
        ('closed', u"Closed")
    ], default='open', readonly=True)

    @api.constrains('start_date', 'qualif_should_be_livred_at', 'should_be_closed_at')
    def check_dates_coherence(self):
        if self.start_date >= self.qualif_should_be_livred_at:
            raise exceptions.ValidationError(_(u"Start date must be before test date."))
        if self.qualif_should_be_livred_at >= self.should_be_closed_at:
            raise exceptions.ValidationError(_(u"Test date must be before prod date."))

    @api.multi
    def _compute_nb_related(self):
        for rec in self:
            rec.nb_tasks = len(rec.task_ids)
            rec.nb_days_tasks = sum([task.planned_hours for task in rec.task_ids])

    @api.multi
    def set_to_livred_in_prod(self):
        self.ensure_one().write({
            'livred_in_prod_at': fields.Datetime.now(),
            'livred_in_prod_by': self.env.user.id,
            'state': 'in_prod',
        })

    @api.multi
    def set_to_livred_in_qualif(self):
        self.ensure_one().write({
            'livred_in_qualif_at': fields.Datetime.now(),
            'livred_in_qualif_by': self.env.user.id,
            'state': 'in_qualif',
        })

    @api.multi
    def close_milestone(self):
        self.ensure_one().write({
            'closed_at': fields.Datetime.now(),
            'closed_by': self.env.user.id,
            'state': 'closed',
        })

    @api.multi
    def reopen(self):
        self.ensure_one().write({'state': 'open'})

    @api.multi
    def see_tasks(self):
        self.ensure_one()
        return {
            'name': u"Tâches de la Milestone %s" % self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.task',
            'target': 'new',
            'domain': [('milestone_id', '=', self.id)]
        }


class ProjectProjectMilestone(models.Model):
    _inherit = 'project.project'

    milestone_ids = fields.One2many('project.milestone', 'project_id', u"Milestones")


class ProjectTaskMilestone(models.Model):
    _inherit = 'project.task'

    milestone_id = fields.Many2one('project.milestone', u"Milestone", track_visibility='onchange')
