# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

MONTH_SELECTION = [('%02d' % number, '%02d' % number) for number in range(1, 13)]

# Do not change year selection here, because it will impact existing data
YEAR_SELECTION = [('%02d' % number, '%02d' % number) for number in range(2019, 2051)]


class OmyCrossoveredBudget(models.Model):
    _inherit = 'crossovered.budget'

    month_from = fields.Selection(MONTH_SELECTION, string=u"Start month")
    year_from = fields.Selection(YEAR_SELECTION, string=u"Start year")
    month_to = fields.Selection(MONTH_SELECTION, string=u"End month")
    year_to = fields.Selection(YEAR_SELECTION, string=u"End year")

    @api.model
    def update_months_years_demo_data(self):
        for budget in self.search([]):
            vals = {
                'month_from': fields.Date.to_string(budget.date_from)[5:7],
                'year_from': fields.Date.to_string(budget.date_from)[:4],
                'month_to': fields.Date.to_string(budget.date_to)[5:7],
                'year_to': fields.Date.to_string(budget.date_to)[:4],
            }
            _logger.info("Correcting demo budget %s (ID=%s) with data %s", budget.display_name, budget.id, vals)
            budget.write(vals)
