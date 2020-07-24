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
from openerp import models, api, fields


class WebUiError(Exception):
    pass


class StockPickingTypeWebUiStockProduct(models.Model):
    _inherit = 'stock.picking.type'

    @api.multi
    def web_ui_get_production_lot_by_name(self, name):
        production_lot = self.env['stock.production.lot'].search([('name', '=ilike', name)])
        if not production_lot:
            raise WebUiError(name, "Aucun article ou numéro de lot/série trouvé")

        return production_lot

    @api.multi
    def web_ui_get_product_info_by_name(self, name, product=None):
        """
        On peut rechercher un article, soit par le nom de son code, soit par son nom, soit par son numéro de série/lot.
        """
        if not product:
            product = self.env['product.product'].search([
                '|', '|',
                ('name', '=ilike', name),
                ('name', '=ilike', name.strip()),
                ('default_code', '=ilike', name)
            ])
        production_lot = self.env['stock.production.lot']
        if not product:
            production_lot = self.web_ui_get_production_lot_by_name(name)
            product = production_lot.product_id

        if len(product) > 1:
            raise WebUiError(name, u"Plusieurs articles ont été trouvés : %s" % ", ".join(product.mapped('name')))
        if len(production_lot) > 1:
            raise WebUiError(name, u"Plusieurs lots ont été trouvés : %s" % ", ".join(production_lot.mapped('name')))

        return product.web_ui_get_product_info_one(production_lot)

    @api.multi
    def web_ui_get_production_info_for_product(self, name, product_id):
        """
        Récupère les infos d'un article via son lot de production.
        """
        name = name.strip()
        production_lot = self.env['stock.production.lot'].search([
            ('name', '=ilike', name),
            ('product_id', '=', product_id)
        ])

        if not production_lot:
            raise WebUiError(name, "Aucun article ou numéro de lot/série trouvé")
        if len(production_lot) > 1:
            raise WebUiError(name, u"Plusieurs lots ont été trouvés : %s" % ", ".join(production_lot.mapped('name')))

        product = self.env['product.product'].browse(product_id)

        return product.web_ui_get_product_info_one(production_lot)

    @api.multi
    def do_validate_scan(self, product_infos):
        """
        Crée un stock.picking dont les stock.move sont remplies grâce aux lignes de scan.
        - stock.picking.type de la vue de scan d'articles.
        - procurement.group commun pour les grouper.
        """
        proc_group = self.env['procurement.group'].create({})
        moves = self.env['stock.move']
        for product_info in product_infos:
            product = self.env['product.product'].browse(product_info.get('id'))
            moves |= self.env['stock.move'].create({
                'name': u"%s (Scanné)" % product.name,
                'picking_type_id': self.id,
                'group_id': proc_group.id,
                'product_id': product.id,
                'product_uom_qty': product_info.get('quantity'),
                'product_uom': product.uom_id.id,
                'location_id': self.env.ref('flux_tendu_config.stock_location_rangement').id,
                'location_dest_id': self.env.ref('stock.stock_location_stock').id,
            })
        moves.action_confirm()
        picking = moves[0].picking_id
        picking.action_assign()

        return picking.name


class ProductProductWebUiStockProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def web_ui_get_product_info_one(self, production_lot=False):
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.display_name,
            'default_code': self.default_code or "-",
            'quantity': 1,
            'lot_id': production_lot and production_lot.id or "",
            'lot_name': production_lot and production_lot.name or "-",
            'tracking': self.tracking,
        }

    @api.multi
    def web_ui_get_product_info(self):
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.display_name,
            'default_code': self.default_code,
            'tracking': self.tracking,
        }


class PosteProduct(models.Model):
    _name = 'poste.product'
    _description = "Poste Product"

    name = fields.Char("Nom")
    description = fields.Char("Description")
    code = fields.Char("Code")
