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

from openerp import fields, models, api

class supplier(models.Model):
    _inherit = 'product.supplierinfo'
    packaging_qty = fields.Float(help="Quantity in the standard packaging", default=1)

class procurement_order_improved(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _calc_new_qty_price(self, procurement, po_line=None, cancel=False):
        (qty, price) = super(procurement_order_improved, self)._calc_new_qty_price(procurement, po_line, cancel)
        list_supplierinfo_ids = self.env['product.supplierinfo'].search([('name', '=', po_line.order_id.partner_id.id),
                                                ('product_tmpl_id', '=', procurement.product_id.product_tmpl_id.id)])
        supplierinfo_id = list_supplierinfo_ids[0]
        packaging_number = supplierinfo_id.packaging_qty
        if packaging_number == 0:
            packaging_number = 1
        qty = max(qty, supplierinfo_id.min_qty)
        if qty % packaging_number != 0:
            qty = (qty//packaging_number+1)*packaging_number
        pricelist_id = po_line.order_id.partner_id.property_product_pricelist_purchase
        price = pricelist_id.with_context(uom = procurement.product_uom.id).price_get(procurement.product_id.id, qty,
                                                                        po_line.order_id.partner_id.id)[pricelist_id.id]
        return qty, price

    @api.model
    def _get_po_line_values_from_proc(self, procurement, partner, company, schedule_date):
        result = super(procurement_order_improved, self)._get_po_line_values_from_proc(procurement,
                                                                                       partner, company, schedule_date)
        list_supplierinfo_ids = self.env['product.supplierinfo'].search([('name', '=', partner.id),
                                                ('product_tmpl_id', '=', procurement.product_id.product_tmpl_id.id)])
        supplierinfo_id = list_supplierinfo_ids[0]
        packaging_number = supplierinfo_id.packaging_qty
        if packaging_number == 0:
            packaging_number = 1
        qty = max(result['product_qty'], supplierinfo_id.min_qty)
        if qty % packaging_number != 0:
            qty = (qty//packaging_number+1)*packaging_number
        result['product_qty'] = qty
        pricelist_id = partner.property_product_pricelist_purchase
        result['price_unit'] = pricelist_id.with_context(uom = procurement.product_uom.id).\
                                                price_get(procurement.product_id.id, qty, partner.id)[pricelist_id.id]
        return result