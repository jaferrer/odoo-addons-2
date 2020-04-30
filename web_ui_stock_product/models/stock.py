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


class StockPickingTypeWebUiStockProduct(models.Model):
    _inherit = 'stock.picking.type'

    @api.multi
    def web_ui_get_product_info_by_name(self, name):
        """
        On peut rechercher un article, soit par le nom de son code, soit par son nom.
        """
        name = name.strip()
        product = self.env['product.product'].search(['|', ('name', '=ilike', name), ('default_code', '=ilike', name)])
        if not product:
            raise WebUiError(name, "Aucun article trouvé")
        if len(product) > 1:
            raise WebUiError(name, "Plusieurs articles ont été trouvés : %s" % ", ".join(product.mapped('name')))
        return product.web_ui_get_product_info_one()


class ProductProductWebUiStockProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def web_ui_get_product_info_one(self):
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'default_code': self.default_code,
            'quantity': 1,
        }


class PosteProduct(models.Model):
    _name = 'poste.product'
    _description = "Poste Product"

    name = fields.Char("Nom")
    description = fields.Char("Description")
    code = fields.Char("Code")
