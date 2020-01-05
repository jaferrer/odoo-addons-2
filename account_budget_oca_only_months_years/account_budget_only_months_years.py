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


from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class OmyCrossoveredBudget(models.Model):
    _inherit = 'crossovered.budget'

    month_from = fields.Selection(required=True)
    year_from = fields.Selection(required=True)
    month_to = fields.Selection(required=True)
    year_to = fields.Selection(required=True)
    date_from = fields.Date(compute='_compute_dates', store=True, required=False)
    date_to = fields.Date(compute='_compute_dates', store=True, required=False)

    @api.multi
    @api.depends('month_from', 'year_from', 'month_to', 'year_to')
    def _compute_dates(self):
        for rec in self:
            month_to_first_day = '%s-%s-01' % (rec.year_to, rec.month_to)
            month_to_first_day = fields.Date.from_string(month_to_first_day)
            rec.date_from = '%s-%s-01' % (rec.year_from, rec.month_from)
            rec.date_to = fields.Date.to_string(month_to_first_day + relativedelta(months=1) - relativedelta(days=1))
