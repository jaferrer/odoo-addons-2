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
from odoo import models, api


class WebUiError(Exception):
    pass


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    @api.model
    def web_ui_get_production_lot_by_name(self, name):
        production_lot = self.env['stock.production.lot'].search([('name', '=ilike', name)])
        if not production_lot:
            raise WebUiError(name, "Aucun article ou numéro de lot/série trouvé")
        return production_lot

    @api.model
    def web_ui_get_tracking_by_name(self, name, product_id):
        name = name.strip()
        production_lot = self.env['stock.production.lot'].search(
            [('name', '=ilike', name), ('product_id', '=', product_id)])
        if not production_lot:
            raise WebUiError(name, "Aucun produit trouvé avec ce numéro")
        return production_lot

    @api.multi
    def web_ui_get_storage_product_info_by_name(self, name, picking_id):
        name = name.strip()
        product = self.env['product.product'].search(['|', ('name', '=ilike', name), ('default_code', '=ilike', name)])
        production_lot = False
        if not product:
            production_lot = self.web_ui_get_production_lot_by_name(name)
            product = production_lot.product
        if not product:
            raise WebUiError(name, "Aucun produit trouvé")
        stock_move_lines = self.env['stock.move.line'].search(
            [('product_id', '=', product.id), ('picking_id', '=', picking_id), ('qty_done', '=', 0)])
        if not stock_move_lines:
            raise WebUiError(name, "Aucun produit trouvé")
        return [move_line.web_ui_get_move_line_info_one(production_lot) for move_line in stock_move_lines]

    @api.multi
    def web_ui_get_storage_location_info_by_name(self, name, move_lines):
        name = name.strip()
        stock_move_line = self.env['stock.move.line'].browse(move_lines).filtered(
            lambda move: move.location_dest_id.barcode == name)
        if not stock_move_line:
            raise WebUiError(name, "Emplacement non valide")
        return stock_move_line[:1].web_ui_get_move_line_info_one()

    @api.multi
    def web_ui_get_storage_add_move(self, move_line_id, quantity):
        stock_move_line = self.env['stock.move.line'].browse(move_line_id)
        stock_move_line.write({
            'qty_done': quantity,
        })

    @api.multi
    def web_ui_get_storage_validate_move(self, picking_id):
        self.env['stock.picking.type'].browse(picking_id).action_done()


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.multi
    def web_ui_get_move_line_info_one(self, production_lot=False):
        self.ensure_one()
        res = {
            'id': self.id,
            'default_code': self.product_id.default_code,
            'product_id': self.product_id.id,
            'name': self.product_id.name,
            'location_id': self.location_dest_id.name,
            'product_barcode': self.product_id.barcode,
            'qty': self.product_uom_qty,
            'tracking': self.product_id.tracking,
        }
        if production_lot:
            res = dict(res, num_lot=production_lot.name)
        return res
