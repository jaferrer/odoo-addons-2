# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import models, fields, api, _ as _t

from odoo.addons.queue_job.job import job

from odoo.tools.safe_eval import safe_eval


class ProjectProject(models.Model):
    _inherit = 'project.project'

    is_using_stock = fields.Boolean(u"Uses stock", default=True)
    location_ids = fields.One2many('stock.location', 'project_id', u"Locations")
    location_id = fields.Many2one('stock.location', u"Location", compute='_compute_location_id')

    @api.multi
    def _compute_location_id(self):
        for rec in self:
            rec.location_id = self._get_location_from_project_id(rec.id)

    @api.model
    def create(self, vals):
        res = super(ProjectProject, self).create(vals)
        if res.is_using_stock:
            res._create_location_from_project()

        return res

    @api.multi
    def _create_location_from_project(self):
        self.ensure_one()
        return self.env['stock.location'].create({
            'name': self.name,
            'location_id': self._get_location_from_project_id(self.subtask_project_id.id).id,
            'active': self.active,
            'project_id': self.id,
        })

    @api.multi
    def _get_location_from_project_id(self, project_id):
        """ Return the first (and only) location related to a project id

        :param project_id: id of the project; if False, an empty stock.location recordset will be retyrned
        :return: recordset of stock.location
        """
        return project_id and self.env['stock.location'].search([
            ('project_id', '=', project_id)
        ], limit=1) or self.env['stock.location']

    @api.multi
    def _sync_location_to_project(self, vals):
        """ Synchronize stock.location value to new values given to a project.project

        :param vals: new vals given to the project.project
        """
        self.ensure_one()
        location = self._get_location_from_project_id(self.id)
        loc_vals = {}
        if 'name' in vals:
            loc_vals['name'] = vals['name']
        if 'active' in vals:
            loc_vals['active'] = vals['active']
        if 'subtask_project_id' in vals:
            loc_vals['location_id'] = self._get_location_from_project_id(vals['subtask_project_id']).id
        return location.write(loc_vals)

    @job
    @api.multi
    def sync_location_to_project_current_values(self):
        """ Force synchronization between location and the project's current values

        Used to manually synchronize project and locations, especially when this module is added to an already existing
        database (every project will have is_using_stock == True but no location_id set
        """
        # If a project p2 as another project p1 as a parent, p1's location MUST be created before p2's, otherwise p2's
        # location will be initiated without any parent location.
        # Because of that, we must sync locations from "roots" to "leaves".
        # To make it simpler and quicker, we use an SQL query to return any record in self, ordered by growing depth, so
        # the lower depth project (ie the roots) will be synced earlier.
        self.env.cr.execute("""
WITH RECURSIVE ordered_projects(id, depth) AS (
    SELECT pp.id, 1
    FROM project_project pp
    WHERE pp.subtask_project_id IS NULL
    UNION ALL
    SELECT pp.id, op.depth + 1
    FROM ordered_projects op
    INNER JOIN project_project pp ON op.id = pp.subtask_project_id
)
SELECT op.id
FROM ordered_projects op
WHERE op.id IN %s
ORDER BY op.depth ASC
        """, (tuple(self.ids),))

        for (project_id,) in self.env.cr.fetchall():
            rec = self.browse(project_id)

            # Sync location for current project
            if not rec.is_using_stock:
                continue
            location = self._get_location_from_project_id(rec.id)
            if not location:
                rec._create_location_from_project()
            else:
                rec._sync_location_to_project({
                    'name': rec.name,
                    'active': rec.active,
                    'subtask_project_id': rec.subtask_project_id.id,
                })

    @api.model
    def action_init_location_per_project(self):
        target_projects = self.search([
            ('is_using_stock', '=', True),
            ('location_ids', '=', False),
        ])
        if target_projects:
            target_projects.with_delay(description=_t("Synchronize locations for all projects"))\
                .sync_location_to_project_current_values()

    @api.multi
    def write(self, vals):
        res = super(ProjectProject, self).write(vals)

        for rec in self:
            if vals.get('is_using_stock'):
                location = self._get_location_from_project_id(rec.id)
                if not location:
                    rec._create_location_from_project()
                else:
                    rec._sync_location_to_project(vals)
            elif 'is_using_stock' not in vals and rec.is_using_stock:
                rec._sync_location_to_project(vals)

        return res

    @api.multi
    def action_show_location_current_stock(self):
        self.ensure_one()
        action = self.env.ref('stock.location_open_quants').read()[0]
        action.update({
            'domain': [('location_id', 'child_of', self.location_id.id)]
        })

        return action

    @api.multi
    def action_show_location_products(self):
        self.ensure_one()
        action = self.env.ref('stock.act_product_location_open').read()[0]
        action.update({
            'context': dict(safe_eval(action['context'], {'active_id': self.location_id.id}),
                            location_id=self.location_id.id
                            ),
        })

        return action
