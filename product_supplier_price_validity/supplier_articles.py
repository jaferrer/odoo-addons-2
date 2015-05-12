# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
import time
from datetime import timedelta, date
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.exceptions import except_orm
from openerp import fields, models, api, _

class product_supplierinfo_improved (models.Model):
    _inherit = "product.supplierinfo"
    validity_date_2 = fields.Date("Validity date", help="Price list validity end date. Does not have any affect on the price calculation.")


class pricelist_partnerinfo_improved (models.Model):
    _inherit = "pricelist.partnerinfo"
    validity_date = fields.Date("Validity date", help="Validity date from that date")
    # active = fields.Boolean("True if this rule is used", compute="_is_active")
    _order = 'min_quantity asc, validity_date asc'

    @api.multi
    def is_active(self):
        self.ensure_one()
        context = self.env.context or {}
        reference_date = context.get('date') or time.strftime('%Y-%m-%d')
        active = True
        list_line2 = self.suppinfo_id.pricelist_ids
        list_line = []
        for item in list_line2:
            if item.min_quantity == self.min_quantity:
                list_line += [item]
        if self.validity_date and self.validity_date > reference_date:
            return False
        for item in list_line:
            if item.validity_date and item.validity_date > self.validity_date and item.validity_date <= reference_date:
                active = False
                break
        return active



class product_pricelist_improved(models.Model):
    _inherit="product.pricelist"

    @api.model
    def _price_rule_get_multi(self, pricelist, products_by_qty_by_partner):
        results = super(product_pricelist_improved, self)._price_rule_get_multi(pricelist, products_by_qty_by_partner)
        context = self.env.context or {}
        date = context.get('date') or time.strftime('%Y-%m-%d')
        for product_id in results.keys():
            price = False
            price_uom_id = False
            qty_uom_id = False
            rule_id = results[product_id][1]
            product = self.env['product.product'].browse(product_id)
            rule = self.env['product.pricelist.item'].browse((results[product_id])[1])
            product_uom_obj = self.env['product.uom']
            if rule.base == -2:
                for product2, qty, partner in products_by_qty_by_partner:
                    if product2 == product:
                        results[product.id] = 0.0
                        # rule_id = False
                        price = False
                        qty_uom_id = context.get('uom') or product.uom_id.id
                        price_uom_id = product.uom_id.id
                        if qty_uom_id != product.uom_id.id:
                            try:
                                qty_in_product_uom = product_uom_obj._compute_qty(
                                    context['uom'], qty, product.uom_id.id or product.uos_id.id)
                            except except_orm:
                                # Ignored - incompatible UoM in context, use default product UoM
                                pass
                        seller = False
                        for seller_id in product.seller_ids:
                            if (not partner) or (seller_id.name.id != partner):
                                continue
                            seller = seller_id
                        if not seller and product.seller_ids:
                            seller = product.seller_ids[0]
                        if seller:
                            qty_in_seller_uom = qty
                            seller_uom = seller.product_uom.id
                            if qty_uom_id != seller_uom:
                                qty_in_seller_uom = product_uom_obj._compute_qty(qty_uom_id, qty, to_uom_id=seller_uom)
                            price_uom_id = seller_uom
                            good_pricelist = False
                            for item in seller.pricelist_ids:
                                if item.min_quantity <= qty_in_seller_uom:
                                    if item.validity_date and item.validity_date <= date:
                                        good_pricelist = item
                                    if not item.validity_date:
                                        if not good_pricelist or item.min_quantity != good_pricelist.min_quantity:
                                            good_pricelist = item
                                else:
                                    break
                            price = good_pricelist.price
                        break
                if price_uom_id and qty_uom_id and rule_id:
                    price = product_uom_obj._compute_price(price_uom_id, price, qty_uom_id)
                    results[product.id] = (price, rule_id)
        return results

class procurement_order(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _get_po_line_values_from_proc(self, procurement, partner, company, schedule_date):
        pricelist_id = partner.property_product_pricelist_purchase
        result = super(procurement_order, self)._get_po_line_values_from_proc(procurement, partner, company, schedule_date)
        qty = result['product_qty']
        uom_id = result['product_uom']
        date = fields.Date.to_string(schedule_date)
        price = pricelist_id.with_context(date=date, uom=uom_id).price_get(procurement.product_id.id, qty, partner.id)[pricelist_id.id]
        result['price_unit'] = price
        return result