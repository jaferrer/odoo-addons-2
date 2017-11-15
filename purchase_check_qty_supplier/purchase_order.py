# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api, exceptions, _
from openerp.tools import float_compare


class CheckQtySupplierPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def create(self, vals):
        result = super(CheckQtySupplierPurchaseOrder, self.with_context(check_product_qty=False)).create(vals)
        if self.env.context.get('check_product_qty', True) and self.state != 'cancel' and 'order_line' in vals:
            self._check_qty_on_order()
        return result

    @api.multi
    def write(self, vals):
        result = super(CheckQtySupplierPurchaseOrder, self.with_context(check_product_qty=False)).write(vals)
        if self.env.context.get('check_product_qty', True) and 'order_line' in vals:
            for rec in self.filtered(lambda it: it.state != 'cancel'):
                rec._check_qty_on_order()
        return result

    def _check_qty_on_order(self):
        for product_id in self.mapped('order_line.product_id'):
            self._check_qty_for_product(product_id)

    def _check_qty_for_product(self, product_id):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for rec in self:
            supplierinfo = product_id.seller_ids.filtered(lambda it: it.name.id == rec.partner_id.id)
            supplierinfo = supplierinfo and supplierinfo[0] or False
            if supplierinfo:
                qty = rec._get_qty_on_order_by_product(product_id.id, supplierinfo)
                if float_compare(supplierinfo.min_qty, qty, precision_digits=precision) > 0 and \
                        float_compare(qty, 0, precision_digits=precision) > 0:
                    raise exceptions.except_orm(
                        _(u"Error!"),
                        _(u'The selected supplier has a minimal quantity set to %s %s for the product %s,'
                          u' you should not purchase less.')
                        % (supplierinfo.min_qty, supplierinfo.product_uom.name, product_id.name)
                    )

    def _get_qty_on_order_by_product(self, product_id, supplierinfo):
        self.ensure_one()
        qty_global = 0
        for order_line in self.env['purchase.order.line'] \
                .search([('order_id', '=', self.id), ('product_id', '=', product_id)]):
            qty_compute = self.env['product.uom']._compute_qty(
                from_uom_id=order_line.product_uom.id,
                qty=order_line.product_qty,
                to_uom_id=supplierinfo.product_uom.id)
            qty_global += qty_compute

        return qty_global


class CheckQtySupplierPurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def create(self, vals):
        result = super(CheckQtySupplierPurchaseOrderLine, self).create(vals)
        if self.env.context.get('check_product_qty', True) \
                and (self.state != 'cancel' or self.order_id.state != 'cancel')\
                and 'product_qty' in vals:
            self.order_id._check_qty_for_product(self.product_id)
        return result

    @api.multi
    def write(self, vals):
        result = super(CheckQtySupplierPurchaseOrderLine, self).write(vals)
        if self.env.context.get('check_product_qty', True) and 'product_qty' in vals:
            for rec in self.filtered(lambda it: it.state != 'cancel' or it.order_id.state != 'cancel'):
                rec.order_id._check_qty_for_product(rec.product_id)
        return result

    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
                            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
                            name=False, price_unit=False, state='draft', context=None):

        product_product = self.pool.get('product.product')
        res_partner = self.pool.get('res.partner')

        result = super(CheckQtySupplierPurchaseOrderLine, self).onchange_product_id(cr, uid, ids,
                                                                                    pricelist_id, product_id, qty,
                                                                                    uom_id,
                                                                                    partner_id,
                                                                                    date_order, fiscal_position_id,
                                                                                    date_planned,
                                                                                    name, price_unit, state,
                                                                                    context=context)
        context_partner = context.copy()
        if partner_id:
            lang = res_partner.browse(cr, uid, partner_id).lang
            context_partner.update({'lang': lang, 'partner_id': partner_id})
        product = product_product.browse(cr, uid, product_id, context=context_partner)
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Unit of Measure')

        # Ugly patch to remove the warning if the qty is less than  the main supplier minimal qty
        # The check is done inside the write method inside purchase.order to check if all qty inside the line is ok
        # You can now create two line with the same supplier with the sum qty is more than the min_qty of the supplier
        if result.get('warning', False) and result['warning']['title'] == _('Warning!'):
            for supplier in product.seller_ids:
                if partner_id and (supplier.name.id == partner_id):
                    supplierinfo = supplier
                    min_qty = self.pool.get('product.uom')._compute_qty(cr, uid,
                                                                        supplierinfo.product_uom.id,
                                                                        supplierinfo.min_qty, to_uom_id=uom_id)
                    if float_compare(min_qty, qty, precision_digits=precision) == 1 and qty:
                        message = _(
                            'The selected supplier has a minimal quantity set to %s %s, you should not purchase less.') \
                            % (supplierinfo.min_qty, supplierinfo.product_uom.name)
                        if result['warning']['message'] == message:
                            del result['warning']
                            result['value'].update({'product_qty': qty})
        return result
