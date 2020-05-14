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

from odoo import models, fields, api


class StockLocation(models.Model):
    _inherit = 'stock.location'

    project_id = fields.Many2one('project.project', u"Project")

    @api.model
    def create(self, vals):
        if vals.get('project_id'):
            project = self.env['project.project'].browse(vals['project_id'])
            if 'name' not in vals:
                vals['name'] = project.name
            if 'location_id' not in vals:
                vals['location_id'] = project.subtask_project_id.location_id.id

        return super(StockLocation, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('project_id'):
            project = self.env['project.project'].browse(vals['project_id'])
            if 'name' not in vals:
                vals['name'] = project.name
            if 'location_id' not in vals:
                vals['location_id'] = project.subtask_project_id.location_id.id

        return super(StockLocation, self).write(vals)
