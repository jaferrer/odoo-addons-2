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
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression


class ProjectMilestone(models.Model):
    _name = 'project.milestone'
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left, qualif_should_be_livred_at, id'

    name = fields.Char(u"Title", required=True)
    active = fields.Boolean(u"Active", default=True)
    project_id = fields.Many2one('project.project', u"Project", required=True)
    task_ids = fields.One2many('project.task', 'milestone_id', u"Task")
    nb_tasks = fields.Integer(u"Nb Task", compute='_compute_nb_related')
    nb_days_tasks = fields.Integer(u"Number of days", compute='_compute_nb_related')
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

    parent_id = fields.Many2one('project.milestone', string=u"Milestone parent", index=True, ondelete='cascade')
    child_id = fields.One2many('project.milestone', 'parent_id', string=u"Sous milestones")
    parent_left = fields.Integer(string='Left Parent', index=True)
    parent_right = fields.Integer(string='Right Parent', index=True)

    @api.multi
    def name_get(self):
        def get_names(mls):
            """ Return the list [mls.name, mls.parent_id.name, ...] """
            res = []
            top_parent = mls and mls[0].project_id or self.env['project.project']
            while mls:
                res.append(mls.name)
                mls = mls.parent_id
                if mls:
                    top_parent = mls.project_id
            return top_parent, res
        result = []
        for rec in self:
            project, names = get_names(rec)
            result.append((rec.id, u"(%s) %s" % (project.name, u" / ".join(reversed(names)))))

        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            # Be sure name_search is symetric to name_get
            milestone_names = name.split(' / ')
            parents = list(milestone_names)
            child = parents.pop()
            domain = [('name', operator, child)]
            if parents:
                names_ids = self.name_search(' / '.join(parents), args=args, operator='ilike', limit=limit)
                milestone_ids = [name_id[0] for name_id in names_ids]
                if operator in expression.NEGATIVE_TERM_OPERATORS:
                    milestones = self.search([('id', 'not in', milestone_ids)])
                    domain = expression.OR([[('parent_id', 'in', milestones.ids)], domain])
                else:
                    domain = expression.AND([[('parent_id', 'in', milestone_ids)], domain])
                for i in range(1, len(milestone_names)):
                    domain = [[('name', operator, ' / '.join(milestone_names[-1 - i:]))], domain]
                    if operator in expression.NEGATIVE_TERM_OPERATORS:
                        domain = expression.AND(domain)
                    else:
                        domain = expression.OR(domain)
            milestones = self.search(expression.AND([domain, args]), limit=limit)
        else:
            milestones = self.search(args, limit=limit)
        return milestones.name_get()

    @api.constrains('start_date', 'qualif_should_be_livred_at', 'should_be_closed_at')
    def check_dates_coherence(self):
        if self.start_date > self.qualif_should_be_livred_at:
            raise ValidationError(_(u"Start date must be before test date."))
        if self.should_be_closed_at and self.qualif_should_be_livred_at > self.should_be_closed_at:
            raise ValidationError(_(u"Test date must be before prod date."))

    @api.multi
    def _compute_nb_related(self):
        for rec in self:
            rec.nb_tasks = len(rec.task_ids)
            rec.nb_days_tasks = sum([task.planned_hours for task in rec.task_ids])

    @api.multi
    def set_to_livred_in_prod(self):
        self.ensure_one()

        if self.child_id and any([o.state in ('open', 'in_qualif') for o in self.child_id]):
            raise UserError(u"Toutes les sous milestons doivent être au moins en production ou fermées!")

        self.write({
            'livred_in_prod_at': fields.Datetime.now(),
            'livred_in_prod_by': self.env.user.id,
            'state': 'in_prod',
        })

    @api.multi
    def set_to_livred_in_qualif(self):
        self.ensure_one()

        if self.child_id and any([o.state == 'open' for o in self.child_id]):
            raise UserError(u"Toutes les sous milestons doivent être au moins en recette, production ou fermées!")

        self.write({
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
    functional_description = fields.Text(u"Description fonctionnelle", translate=True)
    technical_description = fields.Text(u"Description technique")
    has_functional_description = fields.Boolean(related='project_id.has_functional_description', readonly=True)
