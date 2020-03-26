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
#

from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    planned_revenue = fields.Float(string=u"Expected sale")
    probability_revenue = fields.Float(string=u"Expected revenue", compute='_get_probability_revenue', store=True)

    @api.depends('planned_revenue', 'probability')
    def _get_probability_revenue(self):
        for rec in self:
            rec.probability_revenue = rec.planned_revenue * rec.probability / 100
