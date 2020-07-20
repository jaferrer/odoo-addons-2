# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def _select_closest_seller(self, partner_id=False, quantity=0.0, date=None, uom_id=False):
        """ Unlike the _select_seller method, return the product.supplierinfo with the closest min_value """
        self.ensure_one()
        if date is None:
            date = fields.Date.today()
        res = self.env['product.supplierinfo']
        sellers = self.seller_ids
        if self.env.context.get('force_company'):
            sellers = sellers.filtered(
                lambda s: not s.company_id or s.company_id.id == self.env.context['force_company'])
        for seller in sellers:
            # Set quantity in UoM of seller
            quantity_uom_seller = quantity
            if quantity_uom_seller and uom_id and uom_id != seller.product_uom:
                quantity_uom_seller = uom_id._compute_quantity(quantity_uom_seller, seller.product_uom)

            if seller.date_start and seller.date_start > date:
                continue
            if seller.date_end and seller.date_end < date:
                continue
            if partner_id and seller.name not in [partner_id, partner_id.parent_id]:
                continue
            if seller.product_id and seller.product_id != self:
                continue
            # Optimal case: we won't have to order more than needed
            if quantity_uom_seller >= seller.min_qty:
                # If any, we replace :
                # - no former supinfo
                # - the former asked for more product than needed
                # - the former asked for the good quantity but is more expensive
                if not res or res.min_qty > quantity_uom_seller or res.price > seller.price:
                    res = seller
            # Less optimal case: the min_qty threshold is greater than needed quantity
            else:
                # if no former supinfo or if the min_qty to order with this supplierinfo id cheaper than the "res" one,
                # we replace
                if not res or (
                        res.min_qty > quantity_uom_seller and
                        (res.min_qty * res.price) > (seller.min_qty * seller.price)
                ):
                    res = seller

        return res
