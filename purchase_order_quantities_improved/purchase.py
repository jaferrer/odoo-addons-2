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
from openerp.tools.float_utils import float_compare


class supplier(models.Model):
    _inherit = 'product.supplierinfo'
    packaging_qty = fields.Float(help="Quantity in the standard packaging", default=1)


class procurement_order_improved(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _calc_new_qty_price(self, procurement, po_line=None, cancel=False):
        if not po_line:
            po_line = procurement.purchase_line_id

        qty = self.env['product.uom']._compute_qty(procurement.product_uom.id, procurement.product_qty,
                                                   procurement.product_id.uom_po_id.id)
        if cancel:
            qty = -qty

        supplierinfo = self.env['product.supplierinfo']. \
            search([('name', '=', po_line.order_id.partner_id.id),
                    ('product_tmpl_id', '=', po_line.product_id.product_tmpl_id.id)], order='sequence, id', limit=1)

        # Make sure we use the minimum quantity of the partner corresponding to the PO.
        # This does not apply in case of dropshipping
        supplierinfo_min_qty = 0.0
        if po_line.order_id.location_id.usage != 'customer' and supplierinfo:
            supplierinfo_min_qty = self.env['product.uom']. \
                _compute_qty(supplierinfo.product_uom.id, supplierinfo.min_qty,
                             po_line.product_id.uom_po_id.id)

        if supplierinfo_min_qty == 0.0 and not self.env.context.get('focus_on_procurements'):
            qty += po_line.product_qty
        elif self.env.context.get('cancelling_active_proc'):
            qty = sum([x.product_qty for x in po_line.procurement_ids if x.state != 'cancel' and x != procurement])
        else:
            # Recompute quantity by adding existing running procurements.
            for proc in po_line.procurement_ids:
                qty += self.env['product.uom']. \
                    _compute_qty(proc.product_uom.id, proc.product_qty,
                                 proc.product_id.uom_po_id.id) if proc.state == 'running' else 0.0
            qty = max(qty, supplierinfo_min_qty) if qty > 0.0 else 0.0

        price = po_line.price_unit

        if supplierinfo:
            packaging_number = self.env['product.uom']. \
                _compute_qty(supplierinfo.product_uom.id, supplierinfo.packaging_qty,
                             po_line.product_id.uom_po_id.id)
            if float_compare(packaging_number, 0.0, precision_rounding=procurement.product_uom.rounding) == 0:
                packaging_number = 1
            if float_compare(qty, 0.0, precision_rounding=procurement.product_uom.rounding) != 0:
                qty = max(qty, supplierinfo.min_qty)
            if float_compare(qty % packaging_number, 0.0, precision_rounding=procurement.product_uom.rounding) != 0:
                qty = (qty // packaging_number + 1) * packaging_number

        if qty != po_line.product_qty:
            pricelist = po_line.order_id.partner_id.property_product_pricelist_purchase
            price = pricelist.with_context(uom=procurement.product_uom.id). \
                price_get(procurement.product_id.id, qty, po_line.order_id.partner_id.id)[pricelist.id]
        return qty, price

    @api.model
    def _get_po_line_values_from_proc(self, procurement, partner, company, schedule_date):
        result = super(procurement_order_improved, self)._get_po_line_values_from_proc(procurement,
                                                                                       partner, company, schedule_date)
        list_supplierinfo_ids = self.env['product.supplierinfo'].search([('name', '=', partner.id),
                                                                         ('product_tmpl_id', '=',
                                                                          procurement.product_id.product_tmpl_id.id)])
        supplierinfo = list_supplierinfo_ids[0]
        packaging_number = supplierinfo.packaging_qty
        if packaging_number == 0:
            packaging_number = 1
        qty = max(result['product_qty'], supplierinfo.min_qty)
        if qty % packaging_number != 0:
            qty = (qty // packaging_number + 1) * packaging_number
        result['product_qty'] = qty
        pricelist = partner.property_product_pricelist_purchase
        result['price_unit'] = pricelist.with_context(uom=procurement.product_uom.id). \
            price_get(procurement.product_id.id, qty, partner.id)[pricelist.id]
        return result
