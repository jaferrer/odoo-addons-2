# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class DeliveryCarrierTrackingNumber(models.Model):
    _name = 'delivery.carrier.tracking.number'
    _description = 'Tracking number'

    name = fields.Char("Tracking number")
    carrier_id = fields.Many2one('delivery.carrier', string="Carrier")


class ProductTemplateDeliveryTracking(models.Model):
    _inherit = 'product.template'

    delivery_ok = fields.Boolean("Is a delivery mode")


class StockQuantPackageDeliveryTracking(models.Model):
    _inherit = 'stock.quant.package'

    carrier_id = fields.Many2one('delivery.carrier', string="Transporteur")


class DeliveryCarrierDeliveryTracking(models.Model):
    _inherit = 'delivery.carrier'

    image = fields.Binary("Image", default=False)
    number_trackings = fields.Integer("trackings number", compute='_compute_number_trackings')
    sale_id = fields.One2many('sale.order', 'carrier_id', string="Sale")
    number_sales = fields.Integer("sales number", compute='_compute_number_sales')
    package_id = fields.One2many('stock.quant.package', 'carrier_id', string="Package")
    number_package = fields.Integer("packages number", compute='_compute_number_packages')
    product_id = fields.Many2one('product.product', string="Product", domain=[('delivery_ok', '=', True)])

    @api.multi
    def _compute_number_trackings(self):
        res = self.env['delivery.carrier.tracking.number'].read_group(
            [('carrier_id', 'in', self.ids)],
            ['carrier_id'],
            ['carrier_id']
        )
        res = {it['carrier_id'][0]: it['carrier_id_count'] for it in res if it['carrier_id']}

        for rec in self:
            rec.number_trackings = res.get(rec.id, 0)

    @api.multi
    def _compute_number_sales(self):
        res = self.env['sale.order'].read_group(
            [('carrier_id', 'in', self.ids)],
            ['carrier_id'],
            ['carrier_id']
        )
        res = {it['carrier_id'][0]: it['carrier_id_count'] for it in res if it['carrier_id']}

        for rec in self:
            rec.number_sales = res.get(rec.id, 0)

    @api.multi
    def _compute_number_packages(self):
        res = self.env['stock.quant.package'].read_group(
            [('carrier_id', 'in', self.ids)],
            ['carrier_id'],
            ['carrier_id']
        )
        res = {it['carrier_id'][0]: it['carrier_id_count'] for it in res if it['carrier_id']}

        for rec in self:
            rec.number_package = res.get(rec.id, 0)

    @api.multi
    def see_tracking_numbers(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        ctx.update({'default_carrier_id': self.id})
        return {
            'name': "Tracking numbers",
            'type': 'ir.actions.act_window',
            'res_model': 'delivery.carrier.tracking.number',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('carrier_id', '=', self.id)],
            'context': ctx
        }

    @api.multi
    def see_sales(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        ctx.update({'default_carrier_id': self.id})
        return {
            'name': "sale orders",
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('carrier_id', '=', self.id)],
            'context': ctx
        }

    @api.multi
    def see_packages(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        ctx.update({'default_carrier_id': self.id})
        return {
            'name': "packages",
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant.package',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('carrier_id', '=', self.id)],
            'context': ctx
        }
