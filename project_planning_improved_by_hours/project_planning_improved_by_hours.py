# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api


class ProjectPlanningByHoursProject(models.Model):
    _inherit = 'project.task'

    @api.multi
    def schedule_get_date(self, date_ref, nb_days=0, nb_hours=0):
        """This function is overwritten to consider objective_duration of tasks as a number of time units of the
        company."""
        hour_unit = self.env.ref('product.product_uom_hour')
        day_unit = self.env.ref('product.product_uom_day')
        project_time_unit_of_company = self.env.user.company_id.project_time_mode_id
        new_nb_days = nb_days
        new_nb_hours = 0
        if project_time_unit_of_company and project_time_unit_of_company != day_unit:
            new_nb_days = 0
            new_nb_hours = self.env['product.uom']. \
                _compute_qty(project_time_unit_of_company.id, nb_days, hour_unit.id) or 0
        return super(ProjectPlanningByHoursProject, self).schedule_get_date(date_ref, new_nb_days, new_nb_hours)
