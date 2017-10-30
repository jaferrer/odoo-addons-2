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

    @api.multi
    def cancel(self):
        result = super(procurement_order_improved, self).cancel()
        order_line_ids = [proc.purchase_line_id.id for proc in self if proc.purchase_line_id]
        order_lines = self.env['purchase.order.line'].search([('id', 'in', order_line_ids),
                                                              ('state', '=', 'draft')])
        order_lines.update_qty_price()
        return result

    @api.multi
    def make_po(self):
        result = super(procurement_order_improved, self).make_po()
        order_line_ids = [proc.purchase_line_id.id for proc in self if proc.purchase_line_id]
        order_lines = self.env['purchase.order.line'].search([('id', 'in', order_line_ids),
                                                              ('state', '=', 'draft')])
        order_lines.update_qty_price()
        return result


class purchase_order_line_improved(models.Model):
    _inherit = 'purchase.order.line'

    @api.multi
    def update_qty_price(self):
        procs_to_cancel = self.env.context.get('cancelling_procs', self.env['procurement.order'])
        for rec in self:
            supplierinfo = self.env['product.supplierinfo']. \
                search([('name', '=', rec.order_id.partner_id.id),
                        ('product_tmpl_id', '=', rec.product_id.product_tmpl_id.id)], order='sequence, id', limit=1)
            # Make sure we use the minimum quantity of the partner corresponding to the PO.
            # This does not apply in case of dropshipping
            supplierinfo_min_qty = 0.0
            if rec.order_id.default_location_dest_id_usage != 'customer' and supplierinfo:
                supplierinfo_min_qty = self.env['product.uom']. \
                    _compute_qty(supplierinfo.product_uom.id, supplierinfo.min_qty, rec.product_id.uom_po_id.id)
            if supplierinfo_min_qty == 0.0 and not self.env.context.get('focus_on_procurements'):
                qty = rec.product_qty
            else:
                # Recompute quantity by adding existing running procurements.
                qty = 0
                for proc in rec.procurement_ids:
                    if proc.state in ['running', 'confirmed'] and proc not in procs_to_cancel:
                        if proc.product_uom != proc.product_id.uom_po_id:
                            qty += self.env['product.uom']._compute_qty(proc.product_uom.id, proc.product_qty,
                                                                        proc.product_id.uom_po_id.id)
                        else:
                            qty += proc.product_qty
                qty = max(qty, supplierinfo_min_qty) if qty > 0.0 else 0.0

            # Let's compute price
            price = rec.price_unit
            if supplierinfo:
                packaging_number = self.env['product.uom']. \
                    _compute_qty(supplierinfo.product_uom.id, supplierinfo.packaging_qty,
                                 rec.product_id.uom_po_id.id)
                if float_compare(packaging_number, 0.0, precision_rounding=rec.product_uom.rounding) == 0:
                    packaging_number = 1
                if float_compare(qty, 0.0, precision_rounding=rec.product_uom.rounding) != 0:
                    qty = max(qty, supplierinfo.min_qty)
                if float_compare(qty % packaging_number, 0.0, precision_rounding=rec.product_uom.rounding) != 0:
                    qty = (qty // packaging_number + 1) * packaging_number

            if qty != rec.product_qty:
                pricelist = rec.order_id.partner_id.property_product_pricelist
                price = pricelist.with_context(uom=rec.product_uom.id). \
                    price_get(rec.product_id.id, qty, rec.order_id.partner_id.id)[pricelist.id]
            if rec.product_qty != qty or rec.price_unit != price:
                rec.sudo().write({'product_qty': qty, 'price_unit': price})

    @api.multi
    def write(self, vals):
        # Dirty hack to avoid qty/price update in function propagate_cancels of module purchase
        if vals.get('product_qty') and self.env.context.get('do_not_update_qty'):
            del vals['product_qty']
        if vals.get('price_unit') and self.env.context.get('do_not_update_price'):
            del vals['price_unit']
        return super(purchase_order_line_improved, self).write(vals)

    @api.multi
    def unlink(self):
        # Dirty hack to avoid lines deletion in function propagate_cancels of module purchase
        recorset = self
        if self.env.context.get('do_not_unlink_lines'):
            recorset = self.env['purchase.order.line']
        return super(purchase_order_line_improved, recorset).unlink()
