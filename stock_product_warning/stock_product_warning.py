# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api

class stock_product_warning_product(models.Model):
    _inherit = 'product.template'

    procurement_warning = fields.Boolean("Procurement Warning", help="Check this box to display a warning signal in "
                                                                     "the transfer pop-up of stock operations linked "
                                                                     "to this product")

class stock_product_packop_line(models.Model):
    _inherit = 'stock.pack.operation'

    procurement_warning = fields.Boolean("Procurement Warning", related="product_id.procurement_warning")


class stock_product_transfer_detail_items(models.TransientModel):
    _inherit = 'stock.transfer_details_items'

    procurement_warning = fields.Boolean("Procurement Warning", related="product_id.procurement_warning")
