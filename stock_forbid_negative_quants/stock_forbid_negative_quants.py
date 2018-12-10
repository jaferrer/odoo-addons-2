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

from openerp import models, api, exceptions, _
from openerp.tools import config
from openerp.tools.float_utils import float_round, float_compare


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.model
    def create(self, values):
        dest_location = values.get('location_id', False) and self.env['stock.location'].browse(
            values.get('location_id')) or False
        product = values.get('product_id', False) and self.env['product.product'].browse(
            values.get('product_id')) or False
        if dest_location and dest_location.usage == 'internal' and product and product.type == 'product':
            prec = product.uom_id.rounding
            qty = float_compare(float_round(values.get('qty', 0), precision_rounding=prec), 0,
                                precision_rounding=prec) <= 0
            if (not config["test_enable"] or self.env.context.get('force_forbid_negative_quants')) and qty:
                raise exceptions.except_orm(_("Error !"),
                                            _("Impossible to create quant product in internal location with non "
                                              "positiv quantity."))
        return super(StockQuant, self).create(values)

    @api.multi
    def write(self, values):
        val_location_id = values.get('location_id', False)
        val_qty = values.get('qty', 0)
        val_product_id = values.get('product_id', False)
        for rec in self:
            location_id = val_location_id and self.env['stock.location'].browse(val_location_id) or \
                rec.location_id or False
            qty = val_qty or rec.qty
            product_id = val_product_id and self.env['product.product'].browse(val_product_id) or \
                rec.product_id or False
            prec = product_id.uom_id.rounding
            if location_id and location_id.usage == 'internal' and product_id and \
                    product_id.type == 'product':
                neg = float_compare(float_round(qty, precision_rounding=prec), 0, precision_rounding=prec) <= 0
                if (not config["test_enable"] or self.env.context.get('force_forbid_negative_quants')) and neg:
                    raise exceptions.except_orm(_("Error !"),
                                                _("Impossible to edit quant product in internal location with non "
                                                  "positiv quantity."))
        return super(StockQuant, self).write(values)

    @api.model
    def _quant_create(self, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False,
                      force_location_from=False, force_location_to=False):
        if (not config["test_enable"] or self.env.context.get('force_forbid_negative_quants')) \
                and move.location_id.usage == 'internal' and move.product_id.type == 'product':
            prec = move.product_id.uom_id.rounding
            if float_compare(float_round(qty, precision_rounding=prec), 0, precision_rounding=prec) == 0:
                raise exceptions.except_orm(
                    _("Error !"),
                    _("You are not allowed to create null quants. "
                      "Product: %s, quantity: %s, Location: %s, Lot: %s, Package: %s. "
                      "Please contact your technical support.") % (
                        move.product_id.display_name,
                        qty,
                        move.location_id.complete_name,
                        lot_id and self.env['stock.production.lot'].browse(lot_id).name or "-",
                        src_package_id and self.env['stock.quant.package'].browse(src_package_id).name or "-",
                    )
                )
            raise exceptions.except_orm(
                _("Error !"),
                _("You are not allowed to move products quants that are not available. "
                  "If the quants are available, check that package, owner and lot no. match. "
                  "Product: %s, Missing quantity: %s, Location: %s, Lot: %s, Package: %s.") % (
                    move.product_id.display_name,
                    qty,
                    move.location_id.complete_name,
                    lot_id and self.env['stock.production.lot'].browse(lot_id).name or "-",
                    src_package_id and self.env['stock.quant.package'].browse(src_package_id).name or "-",
                )
            )
        return super(StockQuant, self)._quant_create(qty, move, lot_id, owner_id, src_package_id, dest_package_id,
                                                     force_location_from, force_location_to)

    @api.model
    def _quant_split(self, quant, qty):
        prec = quant.product_id.uom_id.rounding
        result = super(StockQuant, self)._quant_split(quant, qty)
        old_neg = float_compare(float_round(quant.qty, precision_rounding=prec), 0, precision_rounding=prec) <= 0
        new_neg = False
        if result:
            new_neg = float_compare(float_round(result.qty, precision_rounding=prec), 0, precision_rounding=prec) <= 0
        if (not config["test_enable"] or self.env.context.get('stock_forbid_negative_quants')) \
                and (old_neg or new_neg) and quant.product_id.type == 'product':
            raise ValueError(_("Quant split: you are not allowed to create a negative or null quant. "
                               "Product: %s, Quant qty: %s, Required reduction to: %s, Location: %s,"
                               " Lot: %s, Package: %s") % (quant.product_id.display_name, quant.qty, qty,
                                                           quant.location_id.complete_name, quant.lot_id.name or '-',
                                                           quant.package_id.name or '-'))
        return result
