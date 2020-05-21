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

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ProjectMilestone(models.Model):
    _name = 'project.milestone'
    _order = 'qualif_should_be_livred_at, id'

    name = fields.Char(u"Title", required=True)
    active = fields.Boolean(u"Active", default=True)
    project_id = fields.Many2one('project.project', u"Project", required=True)
    task_ids = fields.One2many('project.task', 'milestone_id', u"Task")
    nb_tasks = fields.Integer(u"Nb Task", compute='_compute_nb_related')
    nb_days_tasks = fields.Integer(u"Number of days", compute='_compute_nb_related')
    nb_tasks_done = fields.Integer(u"Nb Tasks done", compute='_compute_nb_related')
    start_date = fields.Date(u"Start date", required=True)
    qualif_should_be_livred_at = fields.Date(u"Should be in Test at", required=True)
    should_be_closed_at = fields.Date(u"Should be in Prod at", required=True)
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
    ], default='open', readonly=True, required=True)

    description = fields.Html(u"Description", translate=True)
    qualif_should_be_livred_at_internal = fields.Date(u"Should be in technical test at (internal)")
    referent_id = fields.Many2one('res.users', string=u"Référent", required=True, default=lambda self: self.env.user)

    @api.multi
    def name_get(self):
        return [(rec.id, u"%s (%s)" % (rec.name, rec.project_id.name)) for rec in self]

    @api.constrains('start_date', 'qualif_should_be_livred_at', 'should_be_closed_at')
    def check_dates_coherence(self):
        for rec in self:
            if rec.start_date > rec.qualif_should_be_livred_at:
                raise ValidationError(_(u"Start date must be before test date."))
            if rec.should_be_closed_at and rec.qualif_should_be_livred_at > rec.should_be_closed_at:
                raise ValidationError(_(u"Test date must be before prod date."))

    @api.multi
    def _compute_nb_related(self):
        for rec in self:
            rec.nb_tasks = len(rec.task_ids)
            rec.nb_days_tasks = sum([task.planned_hours for task in rec.task_ids])
            rec.nb_tasks_done = len([task for task in rec.task_ids if task.stage_id.type == 'done'])

    @api.multi
    def set_to_livred_in_prod(self):
        self.write({
            'livred_in_prod_at': fields.Datetime.now(),
            'livred_in_prod_by': self.env.user.id,
            'state': 'in_prod',
        })

    @api.multi
    def set_to_livred_in_qualif(self):
        self.write({
            'livred_in_qualif_at': fields.Datetime.now(),
            'livred_in_qualif_by': self.env.user.id,
            'state': 'in_qualif',
        })

    @api.multi
    def close_milestone(self):
        self.write({
            'closed_at': fields.Datetime.now(),
            'closed_by': self.env.user.id,
            'state': 'closed',
        })

    @api.multi
    def reopen(self):
        self.write({'state': 'open'})

    @api.multi
    def see_tasks(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        ctx['search_default_milestone_id'] = self.id
        return {
            'name': u"Tâches de la Milestone %s" % self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'project.task',
            'domain': [],
            'context': ctx
        }


class ProjectProjectMilestone(models.Model):
    _inherit = 'project.project'

    milestone_ids = fields.One2many('project.milestone', 'project_id', u"Milestones")
    nb_milestones = fields.Integer(string=u"Number of milestones", compute='_compute_nb_milestones')
    has_functional_description = fields.Boolean(u"Activer la communication des tâches", default=False)

    @api.multi
    def _compute_nb_milestones(self):
        for rec in self:
            rec.nb_milestones = len([milestone for milestone in rec.milestone_ids if milestone.state != 'closed'])

    @api.multi
    def milestone_tree_view(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        ctx['search_default_project_id'] = self.id
        ctx['default_project_id'] = self.id
        ctx['search_default_open'] = True
        return {
            'name': _(u"Milestones for project %s") % self.display_name,
            'res_model': 'project.milestone',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'context': ctx,
        }


class ProjectTaskMilestone(models.Model):
    _inherit = 'project.task'

    milestone_id = fields.Many2one('project.milestone', u"Milestone", track_visibility='onchange')
    qualif_should_be_livred_at = fields.Date(u"Should be in Test at",
                                             related="milestone_id.qualif_should_be_livred_at",
                                             readonly=True, store=True)
    should_be_closed_at = fields.Date(u"Should be in Prod at", related="milestone_id.should_be_closed_at",
                                      readonly=True, store=True)
    should_be_test_before = fields.Date(u"Should be tested before", related="milestone_id.should_be_test_before",
                                        readonly=True, store=True)
    functional_description = fields.Html(u"Description fonctionnelle", translate=True)
    technical_description = fields.Text(u"Description technique")
    has_functional_description = fields.Boolean(related='project_id.has_functional_description', readonly=True)
