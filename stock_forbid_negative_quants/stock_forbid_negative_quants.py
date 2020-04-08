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
    def _check_env_config_negative_quant(self):
        return not config["test_enable"] or self.env.context.get('force_forbid_negative_quants')

    @api.model
    def create(self, vals):
        if not self._check_env_config_negative_quant():
            return super(StockQuant, self).create(vals)

        dest_location = self.env['stock.location'].browse(vals.get('location_id', False))
        product = self.env['product.product'].browse(vals.get('product_id', False))
        self._assert_not_negative(dest_location, product, vals.get('qty', 0))
        return super(StockQuant, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self._check_env_config_negative_quant():
            return super(StockQuant, self).write(vals)

        for rec in self:
            location = self.env['stock.location'].browse(vals.get('location_id', rec.location_id.id))
            product = self.env['product.product'].browse(vals.get('product_id', rec.product_id.id))
            self._assert_not_negative(location, product, vals.get('qty', rec.qty))
        return super(StockQuant, self).write(vals)

    @api.model
    def _assert_not_negative(self, location, product, qty):
        if location and product and location.usage == 'internal' and product.type == 'product':
            prec = product.uom_id.rounding
            if float_compare(float_round(qty, precision_rounding=prec), 0, precision_rounding=prec) <= 0:
                raise exceptions.UserError(
                    _(u"Impossible to edit/create quant product in internal location with non positiv quantity.")
                )

    @api.model
    def _quant_create(self, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False,
                      force_location_from=False, force_location_to=False):
        if self._check_env_config_negative_quant() \
                and move.location_id.usage == 'internal' \
                and move.product_id.type == 'product':
            prec = move.product_id.uom_id.rounding
            if float_compare(float_round(qty, precision_rounding=prec), 0, precision_rounding=prec) == 0:
                raise exceptions.UserError(
                    _(u"You are not allowed to create null quants. "
                      u"Product: %s, quantity: %s, Location: %s, Lot: %s, Package: %s. "
                      u"Please contact your technical support.") % (
                        move.product_id.display_name,
                        qty,
                        move.location_id.complete_name,
                        lot_id and self.env['stock.production.lot'].browse(lot_id).name or "-",
                        src_package_id and self.env['stock.quant.package'].browse(src_package_id).name or "-",
                    )
                )
            raise exceptions.UserError(
                _(u"You are not allowed to move products quants that are not available. "
                  u"If the quants are available, check that package, owner and lot no. match. "
                  u"Product: %s, Missing quantity: %s, Location: %s, Lot: %s, Package: %s.") % (
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
        if self._check_env_config_negative_quant() and (old_neg or new_neg) and quant.product_id.type == 'product':
            raise ValueError(_(u"Quant split: you are not allowed to create a negative or null quant. "
                               u"Product: %s, Quant qty: %s, Required reduction to: %s, Location: %s,"
                               u" Lot: %s, Package: %s") % (quant.product_id.display_name, quant.qty, qty,
                                                            quant.location_id.complete_name, quant.lot_id.name or '-',
                                                            quant.package_id.name or '-'))
        return result
