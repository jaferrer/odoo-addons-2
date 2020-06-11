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


class MergePurchasePlanningWizard(models.TransientModel):
    _name = 'merge.purchase.planning.wizard'
    _description = "Merge Planning Wizard"

    period_id = fields.Many2one('period.planning', readonly=True)
    season_id = fields.Many2one('res.calendar.season', u"Season", readonly=True)
    year_id = fields.Many2one('res.calendar.year', u"Year", readonly=True)
    purchase_planning_id = fields.Many2one('period.planning', string="Purchase planning")

    @api.model
    def new(self):
        self.period_id.create_purchase_planning()

    @api.multi
    def merge(self):
        return self.period_id.merge_purchase_planning(self.purchase_planning_id)
