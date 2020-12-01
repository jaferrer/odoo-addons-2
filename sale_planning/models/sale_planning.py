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


class SalePlanning(models.Model):
    _name = 'sale.planning'
    _description = "Sale Planning"
    _rec_name = 'period_id'

    product_id = fields.Many2one('product.product', u"Product", required=True, readonly=True)
    stock_qty = fields.Float(u"Quantity in stock", related='product_id.qty_available', readonly=True)
    forecast_qty = fields.Float(u"Forecast quantity", related='product_id.virtual_available', readonly=True)
    period_id = fields.Many2one('period.planning', u"Period", required=True, readonly=True)
    sale_last_year = fields.Float(u"Last year sales", required=True, readonly=True)
    sale_qty = fields.Float(u"Quantity to sale")
    reserve_qty = fields.Float(u"Quantity to reserve")
    categ_id = fields.Many2one('product.category', "Product category")
    state = fields.Selection([
        ('draft', u"Draft"),
        ('confirm', "Confirm"),
        ('done', u"Done"),
    ], required=True, readonly=True, default='draft')
    purchase_state = fields.Selection([
        ('draft', u"Draft"),
        ('confirm', u"Confirmed"),
        ('lock', u"Locked"),
        ('done', u"Done"),
    ], related='period_id.purchase_state')

    @api.model_create_multi
    def create(self, vals_list):
        grouped_val_list = {}
        for val in vals_list:
            key = (val['period_id'])
            grouped_val_list.setdefault(key, [])
            grouped_val_list[key].append(val['product_id'])

        result = {}
        for (period_id), product_ids in grouped_val_list.items():
            period = self.env['period.planning'].browse(period_id)
            start_date, end_date = period.season_id._get_duration(period.year_id.name - 1)
            result_group = self.env['sale.order.line'].read_group(
                domain=[
                    ('order_id.confirmation_date', '>=', start_date),
                    ('order_id.confirmation_date', '<=', end_date),
                    ('product_id', 'in', list(set(product_ids))),
                ],
                fields=['product_uom_qty'],
                groupby=['product_id'],
            )
            for result in result_group:
                result[(period_id, result['product_id'][0])] = result['product_uom_qty']
        for vals in vals_list:
            vals['sale_last_year'] = result.get((vals['period_id'], vals['product_id']), 0)
        return super(SalePlanning, self).create(vals_list)

    @api.multi
    def write(self, vals):
        vals['state'] = "draft"
        for rec in self:
            rec.period_id.write({'sale_state': "draft"})
        super(SalePlanning, self).write(vals)

    @api.multi
    def confirm_forecast(self):
        """
        Confirm selected Sale Plannings via the Sale Confirm Forecast Wizard.
        """
        for rec in self:
            wizard = self.env['confirm.period.wizard'].create({'period_id': rec.period_id.id})
            wizard.confirm_sale_forecast()
