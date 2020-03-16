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


class PurchasePlanningWizard(models.TransientModel):
    _name = 'purchase.planning.wizard'
    _description = "Purchase Planning Wizard"

    season_id = fields.Many2one('res.calendar.season', u"Season")
    year_id = fields.Many2one('res.calendar.year', u"Year")

    @api.multi
    def generate_purchase_forecast(self):
        self.ensure_one()
        products = self.env['product.product']._get_products_for_purchase_forecast()
        purchase_plannings = self.env['purchase.planning']
        for product in products:
            purchase_plannings |= self.env['purchase.planning'].create({
                'season_id': self.season_id.id,
                'year_id': self.year_id.id,
                'product_id': product.id,
                'supplier_id': product.seller_ids[:1].id,
            })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Forecast',
            'res_model': 'purchase.planning',
            'view_type': 'form',
            'view_mode': 'tree',
            'context': self.env.context,
            'domain': [('id', 'in', purchase_plannings.ids)],
            'target': 'current',
        }
