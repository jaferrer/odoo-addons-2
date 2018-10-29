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

from openerp import fields, models, api, _


class ProjectMilestone(models.Model):
    _inherit = 'project.milestone'

    nb_issues = fields.Integer(u"Number of issues", compute='_compute_nb_issues')
    issue_ids = fields.One2many('project.issue', 'milestone_id', u"Issues", readonly=True)

    @api.multi
    def _compute_nb_issues(self):
        for rec in self:
            rec.nb_issues = len(rec.issue_ids)


class ProjectIssueMilestone(models.Model):
    _inherit = 'project.issue'

    milestone_id = fields.Many2one('project.milestone', u"Milestone", domain=[('state', '!=', 'closed')])
    milestone_name = fields.Char(related='milestone_id.name', string=u"Milestone", readonly=True)
    milestone_state = fields.Selection(related='milestone_id.state', string=u"Milestone State", readonly=True)

    @api.onchange('milestone_id')
    def onchange_milestone_id(self):
        for rec in self:
            if rec.milestone_id:
                rec.date_deadline = rec.milestone_id.qualif_should_be_livred_at and \
                                    rec.milestone_id.qualif_should_be_livred_at[:10] or False
