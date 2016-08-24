# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api, _
from openerp.tools import float_compare
from openerp.exceptions import ValidationError


class PurchaseOrderResizer(models.TransientModel):
    _name = 'purchase.order.resizer'

    def _get_default_order_ids(self):
        orders = False
        if self.env.context.get('active_model') == 'purchase.order' and self.env.context.get('active_ids'):
            orders = self.env['purchase.order'].browse(self.env.context['active_ids'])
        return orders

    order_ids = fields.Many2many('purchase.order', string="Orders to resize", default=_get_default_order_ids,
                                 required=True)
    resizing_ratio = fields.Float(string="Resizing ratio (%)", required=True)

    @api.multi
    def validate_resizing(self):
        self.ensure_one()
        if any([order.state != 'draft' for order in self.order_ids]):
            raise ValidationError(_("Impossible to resize a not-draft purchase order."))
        resizing_ratio = float(self.resizing_ratio) / 100
        for order in self.order_ids:
            for line in order.order_line:
                product = line.product_id
                qty_to_order = line.product_qty * resizing_ratio
                supplierinfo = product.seller_ids and product.seller_ids[0] or False
                if supplierinfo:
                    qty_to_order = max(supplierinfo.min_qty, qty_to_order)
                    if self.compare(qty_to_order, supplierinfo.packaging_qty, product.uom_id.rounding) != 0:
                        qty_to_order = (qty_to_order // supplierinfo.packaging_qty + 1) * supplierinfo.packaging_qty
                qty_to_order = int(qty_to_order)
                line.product_qty = qty_to_order

    def compare(self, qty_to_order, packaging_qty, rounding):
        float_compare(qty_to_order, (qty_to_order // packaging_qty) * packaging_qty, precision_rounding=rounding)
