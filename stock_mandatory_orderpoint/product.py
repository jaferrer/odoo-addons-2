# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession

from openerp import fields, models, api


@job
def create_needed_orderpoint_for_product(session, model, ids, context):
    session.env['product.product'].with_context(context).search([('id', 'in', ids)])._create_needed_orderpoints()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def create(self, vals):
        product = super(ProductProduct, self).create(vals)
        product.create_needed_orderpoints()
        return product

    @api.multi
    def write(self, vals):
        product = super(ProductProduct, self).write(vals)
        if 'route_ids' in vals:
            self.create_needed_orderpoints()
        return product

    @api.multi
    def create_needed_orderpoints(self, jobify=True):
        if jobify:
            products = self
            while products:
                chunk_products = products[:100]
                products = products[100:]
                create_needed_orderpoint_for_product.delay(ConnectorSession.from_env(self.env), 'product.product',
                                                           chunk_products.ids, dict(self.env.context), )
        else:
            create_needed_orderpoint_for_product(ConnectorSession.from_env(self.env), 'product.product',
                                                 self.ids, dict(self.env.context))

    @api.multi
    def _create_needed_orderpoints(self):
        location_config_ids = self.env['ir.config_parameter'].get_param(
            "stock_location_orderpoint.required_orderpoint_location_ids", default="[]")
        orderpoint_required_location = self.env['stock.location'].browse(eval(location_config_ids))
        for rec in self:
            orderpoint_required_location |= rec.route_ids.mapped('required_orderpoint_location_ids')
            for location in orderpoint_required_location:
                if not self.env['stock.warehouse.orderpoint'].search([('product_id', '=', rec.id),
                                                                      ('location_id', '=', location.id)]):
                    self.env['stock.warehouse.orderpoint'].create(rec._prepare_order_point_data(location))

    @api.multi
    def _prepare_order_point_data(self, location):
        self.ensure_one()
        values = self.env['stock.warehouse.orderpoint'].default_get(self.env['stock.warehouse.orderpoint']._fields)
        values.update({
            'warehouse_id': location.warehouse_id.id or values.get("warehouse_id"),
            'location_id': location.id,
            'product_id': self.id,
            "product_min_qty": 0,
            "product_max_qty": 0,
        })
        return values


class SirailLogistiqueStockLocationRoute(models.Model):
    _inherit = 'stock.location.route'

    required_orderpoint_location_ids = fields.Many2many('stock.location', 'stock_locatoin_route_to_location_ref',
                                                        'route_id', 'location_id',
                                                        string=u"Required Orderpoint Location")
    product_ids = fields.Many2many('product.product', 'stock_route_product', 'route_id', 'product_id',
                                   string=u"Products")

    @api.multi
    def update_orderpoint(self):
        for rec in self:
            rec.product_ids.create_needed_orderpoints()
