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
from openerp import models, api


class WebUiError(Exception):
    pass


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    @api.multi
    def web_ui_get_all_picking_storage(self):
        self.ensure_one()

        list_pickings = []
        pickings = self.env['stock.picking'].search([
            ('picking_type_id', '=', self.id),
            ('state', '=', 'assigned')
        ], order='name')

        for picking in pickings:
            list_pickings.append({
                'id': picking.id,
                'name': picking.name,
                'user': picking.owner_id.name or "-",
                'operation_count': len(picking.pack_operation_product_ids),
            })

        return list_pickings

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
    def web_ui_has_one_operation_left(self, picking_id):
        res = {'empty': False, 'last_operation': None}
        spo = self.env['stock.pack.operation'].read_group(
            [('picking_id', '=', picking_id), ('qty_done', '=', 0)], ['product_id'], ['product_id']
        )
        if not spo:
            res = {'empty': True}
        elif len(spo) == 1:
            product = self.env['product.product'].browse(spo[0]['product_id'][0])
            res = {
                'empty': False,
                'last_operation': product.default_code
            }

        return dict(res)

    @api.multi
    def web_ui_get_storage_product_info_by_name(self, name, picking_id, product=None):
        if not product:
            product = self.env['product.product'].search([
                '|', '|',
                ('name', '=ilike', name),
                ('name', '=ilike', name.strip()),
                ('default_code', '=ilike', name)
            ])
        production_lot = False
        if not product:
            production_lot = self.web_ui_get_production_lot_by_name(name)
            product = production_lot.product
        if not product:
            raise WebUiError(name, "Aucun produit trouvé")
        stock_move_lines = self.env['stock.pack.operation'].search(
            [('product_id', '=', product.id), ('picking_id', '=', picking_id), ('qty_done', '=', 0)])
        if not stock_move_lines:
            raise WebUiError(name, "Aucun produit trouvé")
        return [move_line.web_ui_get_move_line_info_one(production_lot) for move_line in stock_move_lines]

    @api.multi
    def web_ui_get_storage_location_info_by_name(self, name, move_lines):
        name = name.strip()
        stock_move_line = self.env['stock.pack.operation'].browse(move_lines).filtered(
            lambda move: move.location_dest_id.barcode == name)
        if not stock_move_line:
            raise WebUiError(name, "Emplacement non valide")
        return stock_move_line[:1].web_ui_get_move_line_info_one()

    @api.multi
    def web_ui_get_storage_new_location_info_by_name(self, name, move_line):
        self.ensure_one()
        name = name.strip()
        location = self.env['stock.location'].search([('barcode', '=ilike', name)])
        stock_move_line = self.env['stock.pack.operation'].browse(move_line)
        if not location:
            raise WebUiError(name, "Emplacement non valide")
        if not stock_move_line:
            raise WebUiError(name, "Problème avec la ligne")
        move_line_infos = stock_move_line.web_ui_get_move_line_info_one()
        move_line_infos.update({'location_id': location.name})
        return move_line_infos

    @api.multi
    def web_ui_get_storage_location_id_by_name(self, name):
        """
        Recherche un emplacement par son barcode.
        """
        name = name.strip()
        location = self.env['stock.location'].search([('barcode', '=ilike', name)])
        if not location:
            raise WebUiError(name, u"Aucun emplacement n'a été trouvé : %s" % ", ".join(location.mapped('barcode')))
        if len(location) > 1:
            raise WebUiError(name, u"Plusieurs emplacements ont été trouvés : %s" % ", ".join(
                location.mapped('barcode')))

        return location.id

    @api.multi
    def web_ui_get_storage_add_move(self, move_line_id, quantity):
        stock_move_line = self.env['stock.pack.operation'].browse(move_line_id)
        stock_move_line.write({
            'qty_done': quantity,
        })

    @api.multi
    def web_ui_get_storage_validate_move(self, picking_id):
        if picking_id != '0':
            self.env['stock.picking'].browse(picking_id).action_done()


# On utilise le nom StockMoveLine pour parler des stock.pack.operation pour
# volontairement garder plus de similarites entre le module v9 et v12
class StockMoveLine(models.Model):
    _inherit = 'stock.pack.operation'

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
            'qty_todo': self.product_qty,
            'qty_done': self.qty_done,
            'tracking': self.product_id.tracking,
        }
        if production_lot:
            res = dict(res, num_lot=production_lot.name)
        return res

    @api.multi
    def change_location_from_scan_storage(self, location_name):
        """
        Modifie l'emplacement d'origine du move line.
        """
        self.ensure_one()
        location_id = self.picking_id.picking_type_id.web_ui_get_storage_location_id_by_name(location_name)
        self.location_dest_id = self.env['stock.location'].browse(location_id)
        return {'name': self.location_dest_id.name}
