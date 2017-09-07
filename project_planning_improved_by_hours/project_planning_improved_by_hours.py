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
    _inherit = 'project.project'

    @api.multi
    def schedule_get_date(self, date_ref, nb_days=0, nb_hours=0):
        """This function is overwritten to consider planned_duration of tasks as a number of time units of the
        company."""
        hour_unit = self.env.ref('')
        project_time_unit_of_company = self.env.user.company_id.project_time_unit_id
        planned_duration_project_uom = nb_days
        new_nb_days = nb_days
        new_nb_hours = nb_hours
        if hour_unit and project_time_unit_of_company and planned_duration_project_uom:
            new_nb_hours = self.env['product.uom']._compute_qty(project_time_unit_of_company.id, nb_days, hour_unit.id)
            new_nb_days = 0
        return super(ProjectPlanningByHoursProject, self).schedule_get_date(date_ref, new_nb_days, new_nb_hours)
