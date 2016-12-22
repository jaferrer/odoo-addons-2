# -*- coding: utf8 -*-
#
# Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api, _
from openerp.tools.sql import drop_view_if_exists


class StockInventorySpecific(models.Model):
    _inherit = 'stock.inventory'

    def _get_available_filters(self):
        """
           This function will return the list of filter allowed according to the options checked
           in 'Settings\Warehouse'.

           :rtype: list of tuple
        """
        # default available choices
        res_filter = super(StockInventorySpecific, self)._get_available_filters()
        res_filter.append(('inventory_specific', 'Selected Products'))
        return res_filter

    filter = fields.Selection(selection=_get_available_filters)
    specify_product_ids = fields.Many2many("product.product", string="Selected Products")

    @api.model
    def _get_inventory_lines(self, inventory):

        vals = []
        if inventory.filter == 'inventory_specific':
            location_obj = self.env['stock.location']
            product_obj = self.env['product.product']
            location_ids = location_obj.search([('id', 'child_of', [inventory.location_id.id])])
            domain = ' location_id in %s'
            args = (tuple(location_ids.ids),)
            if inventory.partner_id:
                domain += ' and owner_id = %s'
                args += (inventory.partner_id.id,)
            if inventory.lot_id:
                domain += ' and lot_id = %s'
                args += (inventory.lot_id.id,)
            if inventory.specify_product_ids:
                domain += ' and product_id in %s'
                args += (tuple(inventory.specify_product_ids.ids),)
            if inventory.package_id:
                domain += ' and package_id = %s'
                args += (inventory.package_id.id,)

            self.env.cr.execute('''
               SELECT product_id, sum(qty) AS product_qty, location_id, lot_id AS prod_lot_id,
               package_id, owner_id AS partner_id
               FROM stock_quant WHERE''' + domain + '''
               GROUP BY product_id, location_id, lot_id, package_id, partner_id
            ''', args)

            for product_line in self.env.cr.dictfetchall():
                # replace the None the dictionary by False, because falsy values are tested later on
                for key, value in product_line.items():
                    if not value:
                        product_line[key] = False
                product_line['inventory_id'] = inventory.id
                product_line['theoretical_qty'] = product_line['product_qty']
                if product_line['product_id']:
                    product = product_obj.browse(product_line['product_id'])
                    product_line['product_uom_id'] = product.uom_id.id
                vals.append(product_line)
        else:
            vals = super(StockInventorySpecific, self)._get_inventory_lines(inventory)
        return vals


class StockSpecificProductInventory(models.Model):
    _name = 'stock.specific.product.inventory'
    _auto = False

    stock_warehouse_id = fields.Many2one('stock.warehouse', readonly=True, index=True, string='Warehouse')
    product_id = fields.Many2one('product.product', readonly=True, index=True, string='Product')
    category = fields.Char('Product Category', readonly=True, store=True)
    qty = fields.Integer('Total', readonly=True)
    invetory_date = fields.Datetime('Last Inventory Date', readonly=True)
    move_stock_date = fields.Datetime('Last Move Date', readonly=True)
    value_stock = fields.Float('Stock Value', readonly=True)

    def init(self, cr):
        drop_view_if_exists(cr, "stock_specific_product_inventory")
        cr.execute("""CREATE OR REPLACE VIEW stock_specific_product_inventory AS (
  WITH RECURSIVE top_parent(loc_id, top_parent_id) AS (
    SELECT
      sl.id AS loc_id,
      sl.id AS top_parent_id
    FROM
      stock_location sl
      LEFT JOIN stock_location slp ON sl.location_id = slp.id
    WHERE
      sl.usage = 'internal'
    UNION
    SELECT
      sl.id AS loc_id,
      tp.top_parent_id
    FROM
      stock_location sl, top_parent tp
    WHERE
      sl.usage = 'internal' AND sl.location_id = tp.loc_id
  )
  SELECT
    stock_warehouse.id :: TEXT || '-' || product_product.id :: TEXT AS id,
    stock_warehouse.id                                              AS stock_warehouse_id,
    product_product.id                                              AS product_id,
    product_category.name                                           AS category,
    sum(stock_quant.qty)                                            AS qty,
    sum(stock_quant.qty * stock_quant.cost)                         AS value_stock,
    max(stock_inventory.date)                                       AS invetory_date,
    max(stock_move.date)                                            AS move_stock_date
  FROM stock_warehouse
    INNER JOIN top_parent ON stock_warehouse.lot_stock_id = top_parent.top_parent_id
    INNER JOIN stock_quant ON stock_quant.location_id = top_parent.loc_id
    INNER JOIN product_product ON product_product.id = stock_quant.product_id
    INNER JOIN product_template ON product_product.product_tmpl_id = product_template.id
    INNER JOIN product_category ON product_template.categ_id = product_category.id
    LEFT JOIN (SELECT
                 location_id,
                 max(date) AS date
               FROM stock_inventory s
               GROUP BY location_id) stock_inventory ON stock_inventory.location_id = top_parent.loc_id
    LEFT JOIN (SELECT
                 location_id,
                 product_id,
                 max(date) AS date
               FROM stock_move m
               GROUP BY location_id, product_id) stock_move
      ON stock_move.location_id = top_parent.loc_id AND stock_move.product_id = product_product.id
  GROUP BY stock_warehouse.id, product_product.id, product_category.name)
        """)

    @api.model
    def create_inventory(self):
        product_view_ids = self.env.context.get('active_ids', [])
        if not product_view_ids:
            return []
        product_views = self.env['stock.specific.product.inventory'].browse(product_view_ids)
        action = {
            'name': _('Inventory Adjustments'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.inventory',
            'type': 'ir.actions.act_window'
        }
        result = []
        for warehouse in self.env['stock.warehouse'].search([]):
            products = product_views.filtered(lambda x: x.stock_warehouse_id == warehouse). \
                mapped(lambda x: x.product_id)
            if products:
                result += [self.env['stock.inventory'].create({
                    'specify_product_ids': [(6, 0, products.ids)],
                    'location_id': warehouse.lot_stock_id.id,
                    'filter': 'inventory_specific',
                    'company_id': warehouse.company_id.id,
                    'name': 'inventaire' + '-' + warehouse.name + '-' + fields.Datetime.now()}).id]
        if len(result) == 1:
            action['res_id'] = result[0]
            action['view_mode'] = 'form'
        elif len(result) > 1:
            action['domain'] = [('id', 'in', result)]
        return action
