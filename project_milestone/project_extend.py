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

from openerp import fields, models, api


class ProjectMilestone(models.Model):
    _name = 'project.milestone'

    name = fields.Char(u"Titre de la Milestone")
    active = fields.Boolean(u"Archivé", default=True, readonly=True)
    start_date = fields.Date(u"Date de début")
    project_id = fields.Many2one('project.project', u"Projet")

    task_ids = fields.One2many('project.task', 'milestone_id', u"Tâches", readonly=True)

    nb_tasks = fields.Integer(u"Nb tâches", compute='_compute_nb_related')

    state = fields.Selection([
        ('open', u"Ouverte"),
        ('in_qualif', u"En Qualif"),
        ('in_prod', u"En Prod"),
        ('closed', u"Fermée")
    ], default='open', readonly=True)

    qualif_should_be_livred_at = fields.Date(u"Doit être livée en Qualif le")
    should_be_closed_at = fields.Date(u"Doit être livée en Prod le")

    livred_in_qualif_at = fields.Date(u"Livrée en qualif le", readonly=True)
    livred_in_qualif_by = fields.Many2one('res.users', u"Livrée en qualif par", readonly=True)

    livred_in_prod_at = fields.Date(u"Livrée en Prod le", readonly=True)
    livred_in_prod_by = fields.Many2one('res.users', u"Livrée en Prod par", readonly=True)

    closed_by = fields.Many2one('res.users', u"Livrée en prod par", readonly=True)
    closed_at = fields.Date(u"Fermée le", readonly=True)

    @api.multi
    def _compute_nb_related(self):
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
            'active': False,
        })

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

    milestone_id = fields.Many2one('project.milestone', u"Milestone")
