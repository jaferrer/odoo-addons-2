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
    session.env[model].with_context(context).search([('id', 'in', ids)])._create_needed_orderpoints()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def create_needed_orderpoints(self, jobify=True):
        products = self.search([])
        if jobify:
            while products:
                chunk_products = products[:100]
                products = products[100:]
                create_needed_orderpoint_for_product.delay(ConnectorSession.from_env(self.env), 'product.product',
                                                           chunk_products.ids, dict(self.env.context))
        else:
            create_needed_orderpoint_for_product(ConnectorSession.from_env(self.env), 'product.product',
                                                 products.ids, dict(self.env.context))

    @api.multi
    def _create_needed_orderpoints(self):
        if not self:
            return
        self.env.cr.execute("""SELECT
  op.id,
  sl.company_id
FROM stock_warehouse_orderpoint op
  INNER JOIN stock_location sl ON sl.id = op.location_id AND sl.company_id IS NOT NULL
WHERE op.company_id != sl.company_id""")
        for orderpoint_id, company_id in self.env.cr.fetchall():
            orderpoint = self.env['stock.warehouse.orderpoint'].browse(orderpoint_id)
            orderpoint.write({'company_id': company_id})
        location_config_ids = self.env['ir.config_parameter'].get_param(
            "stock_location_orderpoint.required_orderpoint_location_ids", default="[]")
        orderpoint_required_locations = location_config_ids and self.env['stock.location']. \
            browse(eval(location_config_ids))
        self.env.cr.execute("""WITH product_product_restricted AS (
    SELECT *
    FROM product_product
    WHERE id IN %s),

    config_needed_locations AS (
      SELECT
        pp.id AS product_id,
        sl.id AS location_id
      FROM product_product_restricted pp
        CROSS JOIN stock_location sl
      WHERE sl.id IN %s
      GROUP BY pp.id, sl.id),

    route_needed_locations AS (
      SELECT
        pp.id AS product_id,
        rel2.location_id
      FROM product_product_restricted pp
        INNER JOIN stock_route_product rel ON rel.product_id = pp.product_tmpl_id
        INNER JOIN stock_location_route_to_location_ref rel2 ON rel2.route_id = rel.route_id),

    needed_locations AS (
    SELECT *
    FROM config_needed_locations
    UNION ALL
    SELECT *
    FROM route_needed_locations),

    existing_orderpoints AS (
      SELECT
        loc.*,
        op.id AS orderpoint_id
      FROM needed_locations loc
        LEFT JOIN stock_warehouse_orderpoint op ON op.product_id = loc.product_id AND op.location_id = loc.location_id)

SELECT
  product_id,
  location_id
FROM existing_orderpoints
WHERE orderpoint_id IS NULL""", (tuple(self.ids), tuple(orderpoint_required_locations.ids or [0]),))
        for product_id, location_id in self.env.cr.fetchall():
            product = self.env['product.product'].search([('id', '=', product_id)])
            location = self.env['stock.location'].search([('id', '=', location_id)])
            self.env['stock.warehouse.orderpoint'].create(product._prepare_order_point_data(location))

    @api.model
    def _prepare_order_point_data(self, location):
        self.ensure_one()
        values = self.env['stock.warehouse.orderpoint'].default_get(self.env['stock.warehouse.orderpoint']._fields)
        if location.company_id:
            values['company_id'] = location.company_id.id
        values.update({
            'warehouse_id': location.warehouse_id.id or values.get("warehouse_id"),
            'location_id': location.id,
            'product_id': self.id,
            'product_min_qty': 0,
            'product_max_qty': 0,
        })
        return values


class SirailLogistiqueStockLocationRoute(models.Model):
    _inherit = 'stock.location.route'

    required_orderpoint_location_ids = fields.Many2many('stock.location', 'stock_location_route_to_location_ref',
                                                        'route_id', 'location_id',
                                                        string=u"Required Orderpoint Location")
    product_ids = fields.Many2many('product.product', 'stock_route_product', 'route_id', 'product_id',
                                   string=u"Products")
