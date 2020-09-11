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

from odoo import fields, models, api


class ProjectTaskCoefficient(models.Model):
    _name = 'project.task.coefficient'

    name = fields.Char(u"Name", required=True)
    coefficient = fields.Float(u"Coefficient", required=True)
    active = fields.Boolean(u"Active", default=True)
    project_id = fields.Many2one('project.project', string=u"Project")

    @api.multi
    def name_get(self):
        return [(rec.id, u"%s (%s)" % (rec.name, rec.coefficient)) for rec in self]
