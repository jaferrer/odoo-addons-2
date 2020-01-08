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
    _inherit = 'project.config.settings'

    calc_min_date = fields.Integer(u"Nombre mois avant le calcul", default=6)
    calc_max_date = fields.Integer(u"Nombre mois après le calcul", default=12)

    @api.multi
    def set_default_min_date(self):
        for rec in self:
            value = self.env['ir.config_parameter'].get_param('project_task_charge.calc_min_date', default='6')
            if rec.calc_min_date:
                value = rec.calc_min_date
            rec.env['ir.config_parameter'].set_param('project_task_charge.calc_min_date', value or '6')

    @api.multi
    def get_default_min_date(self, fields):
        return {
            'calc_min_date': int(
                self.env['ir.config_parameter'].get_param('project_task_charge.calc_min_date', default='6'))
        }

    @api.multi
    def set_default_max_date(self):
        for rec in self:
            value = self.env['ir.config_parameter'].get_param('project_task_charge.calc_max_date', default='12')
            if rec.calc_max_date:
                value = rec.calc_max_date
            rec.env['ir.config_parameter'].set_param('project_task_charge.calc_max_date', value or '12')

    @api.multi
    def get_default_max_date(self, fields):
        return {
            'calc_max_date': int(
                self.env['ir.config_parameter'].get_param('project_task_charge.calc_max_date', default='12'))
        }
