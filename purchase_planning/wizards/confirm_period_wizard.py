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

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api


class ConfirmPeriodWizard(models.TransientModel):
    _name = 'confirm.period.wizard'
    _description = "Confirm Period Wizard"

    period_id = fields.Many2one('period.planning', u"Period")

    @api.multi
    def confirm_purchase_forecast(self):
        self.ensure_one()
        # Récupération des lignes purchase_planning correspondant à season + year
        # Création d'une liste si retained_qty > 0
        purchase_plannings = self.period_id.purchase_planning_ids.filtered(lambda r: (r.retained_qty > 0))
        # Récupération des sale_planning associées
        sale_plannings = self.period_id.sale_planning_ids.filtered(lambda r: (r.sale_qty + r.reserve_qty > 0))
        season_date = self.period_id.season_id.name_get()
        # Création des procurement_group
        group = self.env['procurement.group'].create({'name': season_date})
        year = self.period_id.year_id.number
        month = self.period_id.season_id.start_month_id.number
        date_start = date.today() + relativedelta(year=year, month=month, day=1)
        for planning in sale_plannings:
            product = planning.product_id
            stock_location = self.env.ref('stock.stock_location_stock')
            values = {
                'group_id': group,
                'date_planned': date_start,
            }
            self.env['procurement.group'].run(product, planning.sale_qty, product.uom_id, stock_location,
                                              season_date[0][1], season_date[0][1], values)
            planning.write({'state': 'done'})
        for planning in purchase_plannings:
            product = planning.product_id
            stock_location = self.env.ref('stock.stock_location_stock')
            values = {
                'group_id': group,
                'date_planned': date_start,
            }
            self.env['procurement.group'].run(product, planning.retained_qty, product.uom_id, stock_location,
                                              season_date[0][1], season_date[0][1], values)
        # Changement de statut des purchase_planning et des sale_planning
        self.period_id.purchase_planning_ids.write({'state': 'done'})
        self.period_id.sale_planning_ids.write({'state': 'done'})
        self.period_id.write({
            'purchase_state': 'done',
            'sale_state': 'done',
        })
