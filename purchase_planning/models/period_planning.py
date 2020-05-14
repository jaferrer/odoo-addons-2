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
    _name = 'period.planning'
    _description = "Period Planning"
    _order = 'year_id, season_id'

    season_id = fields.Many2one('res.calendar.season', u"Season", required=True)
    year_id = fields.Many2one('res.calendar.year', u"Year", required=True)
    purchase_planning_ids = fields.One2many('purchase.planning', 'period_id', "Purchase planning")
    purchase_state = fields.Selection([
        ('draft', u"Draft"),
        ('done', u"Done"),
    ], required=True, readonly=True, default='draft')
    count_purchase_planning = fields.Integer(compute='_compute_purchase_planning')

    _sql_constraints = [('period_unique', 'unique (season_id, year_id)', u"The period must be unique")]

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            name = rec.season_id.name + " " + str(rec.year_id.number)
            res.append((rec.id, name))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        domain = args or []
        domain += ["|", ("season_id.name", operator, name), ("year_id.number", operator, name)]
        return self.search(domain, limit=limit).name_get()

    @api.multi
    def _compute_purchase_planning(self):
        for rec in self:
            rec.count_purchase_planning = self.env['purchase.planning'].search_count([('period_id', 'in', self.ids)])
