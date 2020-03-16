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


class SalePlanningWizard(models.TransientModel):
    _name = 'sale.planning.wizard'
    _description = "Sale Planning Wizard"

    season_id = fields.Many2one('res.calendar.season', u"Season", required=True)
    year_id = fields.Many2one('res.calendar.year', u"Year", required=True)

    @api.multi
    def generate_sale_forecast(self):
        self.ensure_one()
        # Création de la période
        period_id = self.env['period.planning'].create({
            'season_id': self.season_id.id,
            'year_id': self.year_id.id,
        })
        products = self.env['product.product']._get_products_for_sale_forecast()
        self.env['sale.planning'].create([{
            'period_id': period_id.id,
            'product_id': product.id,
            'state': 'draft',
        } for product in products])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Forecast',
            'res_model': 'sale.planning',
            'view_type': 'form',
            'view_mode': 'tree',
            'context': self.env.context,
            'domain': [('period_id', '=', period_id.id)],
        }
