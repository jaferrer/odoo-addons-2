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
    _name = 'project.milestone'

    name = fields.Char(u"Titre de la Milestone")
    active = fields.Boolean(u"Archivé", default=True, readonly=True)
    start_date = fields.Date(u"Date de début")
    task_ids = fields.One2many('project.task', 'milestone_id', u"Tâches", readonly=True)
    nb_tasks = fields.Integer(u"Number of tasks", compute='_compute_nb_tasks')
    state = fields.Selection([
        ('open', u"Ouverte"),
        ('in_qualif', u"En Qualif"),
        ('in_prod', u"En Prod"),
        ('closed', u"Fermée")
    ], default='open', readonly=True)
    qualif_should_be_livred_at = fields.Date(u"Doit être livée en Qualif le", required=True)
    should_be_closed_at = fields.Date(u"Doit être livée en Prod le", required=True)
    livred_in_qualif_at = fields.Date(u"Livrée en qualif le", readonly=True)
    livred_in_qualif_by = fields.Many2one('res.users', u"Livrée en qualif par", readonly=True,
                                          groups="project_milestone.group_project_milestone_manager")
    livred_in_prod_at = fields.Date(u"Livrée en Prod le", readonly=True)
    livred_in_prod_by = fields.Many2one('res.users', u"Livrée en Prod par", readonly=True,
                                        groups="project_milestone.group_project_milestone_manager")
    closed_by = fields.Many2one('res.users', u"Livrée en prod par", readonly=True,
                                groups="project_milestone.group_project_milestone_manager")
    closed_at = fields.Date(u"Fermée le", readonly=True)

    @api.multi
    def _compute_nb_tasks(self):
        for rec in self:
            rec.nb_tasks = len(rec.task_ids)

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
    def see_tasks(self):
        self.ensure_one()
        return {
            'name': _(u"Tasks of milestone %s") % self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.task',
            'target': 'new',
            'domain': [('milestone_id', '=', self.id)]
        }


class ProjectTaskMilestone(models.Model):
    _inherit = 'project.task'

    milestone_id = fields.Many2one('project.milestone', u"Milestone", domain=[('state', '!=', 'closed')])
    milestone_state = fields.Selection(related='milestone_id.state', string=u"Milestone state", store=True,
                                       readonly=True)
    milestone_name = fields.Char(related='milestone_id.name', string=u"Milestone", readonly=True)

    @api.onchange('milestone_id')
    def onchange_milestone_id(self):
        for rec in self:
            if rec.milestone_id:
                rec.date_deadline = rec.milestone_id.qualif_should_be_livred_at and \
                    rec.milestone_id.qualif_should_be_livred_at[:10] or False
