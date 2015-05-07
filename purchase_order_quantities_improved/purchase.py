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

class procurement_order(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def make_po(self):
	    return super(procurement_order, self.with_context(recalculate=True)).make_po()

    @api.model
    def _get_po_line_values_from_proc(self, procurement, partner, company, schedule_date):
        result = super(procurement_order, self)._get_po_line_values_from_proc(procurement, partner, company, schedule_date)
        uom_obj = self.env['product.uom']
        uom_id = procurement.product_id.uom_po_id.id
        qty = uom_obj._compute_qty(procurement.product_uom.id, procurement.product_qty, uom_id)
        result['product_qty'] = qty
        return result

class purchase_line(models.Model):
    _inherit = 'purchase.order.line'

    @api.multi
    def write(self, vals):
        if self.env.context.get('recalculate') and self.product_qty:
            self.ensure_one()
            global_need = sum([item.product_qty for item in self.procurement_ids]) + vals['product_qty'] - self.product_qty
            global_need = max(self.product_id.seller_qty, global_need)
            packaging_number = self.product_id.seller_ids[0].packaging_qty
            if packaging_number == 0:
                packaging_number = 1
            if global_need % packaging_number != 0:
                global_need = (global_need//packaging_number+1)*packaging_number
            vals['product_qty'] = global_need
        return super(purchase_line, self).write(vals)

    @api.model
    def create(self, vals):
        if self.env.context.get('recalculate'):
            global_need = vals['product_qty']
            product = self.env['product.product'].browse(vals['product_id'])
            minimum_quantity = product.seller_ids[0].min_qty
            packaging_number = product.seller_ids[0].packaging_qty
            global_need = max(minimum_quantity, global_need)
            if packaging_number == 0:
                packaging_number = 1
            if global_need % packaging_number != 0:
                global_need = (global_need//packaging_number+1)*packaging_number
            vals['product_qty'] = global_need
        return super(purchase_line, self).create(vals)