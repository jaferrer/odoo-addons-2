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
from openerp import models, api, fields


class WebUiError(Exception):
    pass


class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    @api.model
    def get_all_picking_batches(self):
        list_batches = []
        picking_batches = self.env['stock.picking.batch'].search(
            [('state', 'in', ('assigned', 'in_progress'))],
            order='name'
        )
        for batch in picking_batches:
            list_batches.append({
                'id': batch.id,
                'name': batch.name,
                'user': batch.user_id.name or "",
                'date': batch.date,
            })

        return list_batches

    @api.model
    def get_batch_move_lines(self, batch_id):
        list_move_lines = []
        picking_batch = self.browse(batch_id)
        batch_move_lines = picking_batch.mapped('picking_ids').mapped('move_line_ids_without_package').filtered(
            lambda x: x.product_uom_qty != x.qty_done).sorted(key=lambda x: (x.location_id.name, x.product_id.name))
        for move_line in batch_move_lines:
            product_infos = self.env['stock.picking.type'].web_ui_get_product_info_by_name(move_line.product_id.name)
            list_move_lines.append({
                'id': move_line.id,
                'location': move_line.location_id.name,
                'location_barcode': move_line.location_id.barcode,
                'product': product_infos,
                'quantity': move_line.product_uom_qty,
                'product_uom': move_line.product_uom_id.name,
                'picking': move_line.picking_id.name,
            })

        return list_move_lines


class StockPickingTypeScanBatch(models.Model):
    _inherit = 'stock.picking.type'

    @api.multi
    def web_ui_get_location_info_by_name_batch(self, name):
        """
        Recherche un emplacement par son barcode.
        """
        name = name.strip()
        location = self.env['stock.location'].search([('barcode', '=ilike', name)])
        if not location:
            raise WebUiError(name, "Aucun emplacement n'a été trouvé : %s" % ", ".join(location.mapped('barcode')))
        if len(location) > 1:
            raise WebUiError(name, "Plusieurs emplacements ont été trouvés : %s" % ", ".join(
                location.mapped('barcode')))

        return {
            'id': location.id,
            'name': location.name,
            'barcode': location.barcode
        }

    @api.multi
    def web_ui_get_picking_info_by_name_batch(self, name):
        """
        On peut rechercher un picking par son nom.
        """
        name = name.strip()
        picking = self.env['stock.picking'].search([('name', '=ilike', name)])
        if not picking:
            raise WebUiError(name, "Aucun transfert n'a été trouvé : %s" % ", ".join(picking.mapped('name')))
        if len(picking) > 1:
            raise WebUiError(name, "Plusieurs transferts ont été trouvés : %s" % ", ".join(picking.mapped('name')))

        return picking.display_name


class StockPickingBatchScanBatch(models.Model):
    _inherit = 'stock.picking.batch'

    @api.multi
    def do_validate_batch_scan(self):
        self.ensure_one()
        self.done()


class StockMoveLineScanBatch(models.Model):
    _inherit = 'stock.move.line'

    @api.multi
    def change_location_from_scan_batch(self, location_id):
        """
        Modifie l'emplacement d'origine du move line.
        """
        self.ensure_one()
        self.location_id = self.env['stock.location'].browse(location_id)

    @api.multi
    def change_qty_to_do_from_scan_batch(self, new_qty_to_do):
        """
        Modifie la quantité à faire du move line pour mettre la quantité sélectionnée dans le scanner.
        """
        self.ensure_one()
        self.product_uom_qty = new_qty_to_do

    @api.multi
    def create_move_line_from_scan_batch(self, qty_left):
        """
        Crée une move line à partir d'une autre dont toute la quantité n'a pas pu être scannée.
        """
        self.ensure_one()
        new_move_line = self.copy({
            'product_uom_qty': qty_left,
            'qty_done': 0,
        })
        self.picking_id.move_line_ids_without_package |= new_move_line
        return {
            'id': new_move_line.id,
            'location': new_move_line.location_id.name,
            'location_barcode': new_move_line.location_id.barcode,
            'product': new_move_line.product_id.display_name,
            'quantity': new_move_line.product_uom_qty,
            'product_uom': new_move_line.product_uom_id.name,
            'picking': new_move_line.picking_id.name,
        }

    @api.multi
    def web_ui_update_odoo_qty_batch(self, qty_done):
        self.ensure_one()
        self.qty_done = qty_done


class PosteBatch(models.Model):
    _name = 'poste.batch'
    _description = "Poste Batch"

    name = fields.Char("Nom")
    description = fields.Char("Description")
    code = fields.Char("Code")
