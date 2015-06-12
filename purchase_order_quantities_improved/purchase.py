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
        if po_line or procurement.purchase_line_id:
            if not po_line:
                po_line = procurement.purchase_line_id
            (qty, price) = super(procurement_order_improved, self)._calc_new_qty_price(procurement, po_line, cancel)
            list_supplierinfo_ids = self.env['product.supplierinfo'].search([('name', '=', po_line.order_id.partner_id.id),
                                                    ('product_tmpl_id', '=', procurement.product_id.product_tmpl_id.id)])
            supplierinfo = list_supplierinfo_ids[0]
            packaging_number = supplierinfo.packaging_qty
            if packaging_number == 0:
                packaging_number = 1
            qty = max(qty, supplierinfo.min_qty)
            if qty % packaging_number != 0:
                qty = (qty//packaging_number+1)*packaging_number
            pricelist = po_line.order_id.partner_id.property_product_pricelist_purchase
            price = pricelist.with_context(uom=procurement.product_uom.id).price_get(procurement.product_id.id, qty,
                                                                            po_line.order_id.partner_id.id)[pricelist.id]
            return qty, price
        return False

    @api.model
    def _get_po_line_values_from_proc(self, procurement, partner, company, schedule_date):
        result = super(procurement_order_improved, self)._get_po_line_values_from_proc(procurement,
                                                                                       partner, company, schedule_date)
        list_supplierinfo_ids = self.env['product.supplierinfo'].search([('name', '=', partner.id),
                                                ('product_tmpl_id', '=', procurement.product_id.product_tmpl_id.id)])
        supplierinfo = list_supplierinfo_ids[0]
        packaging_number = supplierinfo.packaging_qty
        if packaging_number == 0:
            packaging_number = 1
        qty = max(result['product_qty'], supplierinfo.min_qty)
        if qty % packaging_number != 0:
            qty = (qty//packaging_number+1)*packaging_number
        result['product_qty'] = qty
        pricelist = partner.property_product_pricelist_purchase
        result['price_unit'] = pricelist.with_context(uom=procurement.product_uom.id).\
                                                price_get(procurement.product_id.id, qty, partner.id)[pricelist.id]
        return result
