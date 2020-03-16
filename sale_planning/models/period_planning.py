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

from odoo import fields, models, api


class PeriodPlanning(models.Model):
    _inherit = 'period.planning'

    sale_planning_ids = fields.One2many('sale.planning', 'period_id', "Sale planning")
    sale_state = fields.Selection([
        ('draft', u"Draft"),
        ('confirm', u"Confirm"),
        ('done', u"Done"),
    ], required=True, readonly=True, default='draft')
    count_sale_planning = fields.Integer(compute='_compute_sale_planning')

    @api.multi
    def _compute_sale_planning(self):
        for rec in self:
            rec.count_sale_planning = len(rec.sale_planning_ids)
