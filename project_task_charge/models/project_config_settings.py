# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import api, fields, models


class ProjectSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    calc_min_date = fields.Integer(u"Nombre mois avant le calcul", default=6)
    calc_max_date = fields.Integer(u"Nombre mois après le calcul", default=12)

    def set_values(self):
        super(ProjectSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('project_task_charge.calc_min_date', int(self.calc_min_date))
        self.env['ir.config_parameter'].sudo().set_param('project_task_charge.calc_max_date', int(self.calc_max_date))

    @api.model
    def get_values(self):
        res = super(ProjectSettings, self).get_values()
        res.update(
            calc_min_date=int(self.env['ir.config_parameter'].sudo().get_param('project_task_charge.calc_min_date')),
            calc_max_date=int(self.env['ir.config_parameter'].sudo().get_param('project_task_charge.calc_max_date')),
        )
        return res
