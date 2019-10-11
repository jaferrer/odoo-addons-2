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
                error = supplierinfo._is_valid_purchase_qty(product_id, qty, precision)
                if error:
                    raise exceptions.except_orm(_(u"Error!"), error)

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
                and (result.state != 'cancel' or result.order_id.state != 'cancel') \
                and 'product_qty' in vals:
            result.order_id._check_qty_for_product(result.product_id)
        return result

    @api.multi
    def write(self, vals):
        result = super(CheckQtySupplierPurchaseOrderLine, self).write(vals)
        if self.env.context.get('check_product_qty', True) and 'product_qty' in vals:
            for rec in self.filtered(lambda it: it.state != 'cancel' or it.order_id.state != 'cancel'):
                rec.order_id._check_qty_for_product(rec.product_id)
        return result

    @api.model
    def raise_if_not_valid_qty(self, product, partner_id, uom_id, res, qty):
        # Fonction re-écrite pour :
        # - ne pré-remplir la quantité que s'il n'y en a pas de fournie
        # - enlever le message d'erreur (vérification à la commande et non plus à la ligne)
        # - prendre en compte uniquement la première fourniture correspondant au fournisseur choisi, s'il y en a
        # plusieurs (ajout du "break").
        supplierinfo = False
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        qty = qty or 0
        for supplier in product.seller_ids:
            if partner_id and (supplier.name.id == partner_id):
                supplierinfo = supplier
                if supplierinfo.product_uom.id != uom_id:
                    res['warning'] = {'title': _('Warning!'),
                                      'message': _('The selected supplier only sells this product by %s') %
                                                 supplierinfo.product_uom.name }
                min_qty = self.env['product.uom']._compute_qty(supplierinfo.product_uom.id,
                                                               supplierinfo.min_qty,
                                                               to_uom_id=uom_id)
                if float_compare(min_qty, qty, precision_digits=precision) == 1:
                    qty = min_qty
                break
        return res, qty, supplierinfo


class CheckQtySupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    def _is_valid_purchase_qty(self, product_id, qty, precision):
        if float_compare(self.min_qty, qty, precision_digits=precision) > 0 and \
                float_compare(qty, 0, precision_digits=precision) > 0:
            return _(u'The selected supplier has a minimal quantity set to %s %s for the product %s,'
                     u' you should not purchase less.') % (self.min_qty, self.product_uom.name, product_id.name)
        return False
