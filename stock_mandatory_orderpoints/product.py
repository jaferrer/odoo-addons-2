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

from odoo.addons.queue_job.job import job

from odoo import fields, models, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @job
    @api.multi
    def create_needed_orderpoint_for_product(self):
        self._create_needed_orderpoints()

    @api.model
    def create_needed_orderpoints(self, jobify=True):
        products = self.search([])
        if jobify:
            while products:
                chunk_products = products[:100]
                products = products[100:]
                chunk_products.with_delay().create_needed_orderpoint_for_product()
        else:
            products.with_delay().create_needed_orderpoint_for_product()

    @api.multi
    def _create_needed_orderpoints(self):
        if not self:
            return
        self.env.cr.execute("""SELECT op.id,
       sl.company_id
FROM stock_warehouse_orderpoint op
       INNER JOIN stock_location sl ON sl.id = op.location_id AND sl.company_id IS NOT NULL
WHERE op.company_id != sl.company_id""")
        for orderpoint_id, company_id in self.env.cr.fetchall():
            orderpoint = self.env['stock.warehouse.orderpoint'].browse(orderpoint_id)
            orderpoint.write({'company_id': company_id})
        location_config_ids = self.env['ir.config_parameter']. \
            get_param('stock_mandatory_orderpoints.mandatory_orderpoint_location_ids')
        orderpoint_required_locations = location_config_ids and self.env['stock.location'].browse(
            eval(location_config_ids)
        ) or self.env['stock.location']
        if not orderpoint_required_locations:
            return
        self.env.cr.execute("""WITH product_product_restricted AS (
  SELECT pp.*
  FROM product_product pp
         LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
  WHERE pt.type != 'service'
    AND pp.id IN %s),

     config_needed_locations AS (
       SELECT pp.id AS product_id,
              sl.id AS location_id
       FROM product_product_restricted pp
              CROSS JOIN stock_location sl
       WHERE sl.id IN %s
       GROUP BY pp.id, sl.id),

     route_needed_locations AS (
       SELECT pp.id AS product_id,
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
       SELECT loc.*,
              op.id AS orderpoint_id
       FROM needed_locations loc
              LEFT JOIN stock_warehouse_orderpoint op
                        ON op.product_id = loc.product_id AND op.location_id = loc.location_id)

SELECT product_id,
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


class StockLocationRoute(models.Model):
    _inherit = 'stock.location.route'

    mandatory_orderpoint_location_ids = fields.Many2many('stock.location', 'stock_location_route_to_location_ref',
                                                         'route_id', 'location_id',
                                                         string=u"Mandatory Orderpoint Location")
    product_ids = fields.Many2many('product.product', 'stock_route_product', 'route_id', 'product_id',
                                   string=u"Products")


class SirailStockLocation(models.Model):
    _inherit = 'stock.location'

    warehouse_id = fields.Many2one('stock.warehouse', u"Warehouse of the top location", compute='_compute_warehouse')

    @api.multi
    def _compute_warehouse(self):
        for rec in self:
            rec.warehouse_id = rec.get_warehouse()
