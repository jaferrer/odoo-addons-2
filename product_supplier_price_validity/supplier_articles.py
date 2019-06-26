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

from openerp.exceptions import except_orm
from openerp import fields, models, api, _


class productSupplierinfoImproved (models.Model):
    _inherit = "product.supplierinfo"
    validity_date_2 = fields.Date(
        "Validity date",
        help="Price list validity end date. Does not have any affect on the price calculation.")


class pricelist_partnerinfo_improved (models.Model):
    _inherit = "pricelist.partnerinfo"
    _order = 'min_quantity asc, validity_date asc'

    validity_date = fields.Date("Validity date", help="Validity date from that date")
    active_line = fields.Boolean("True if this rule is used", store=True, compute="_is_active_line")
    force_inactive = fields.Boolean(string="Inactive Price")

    @api.multi
    @api.depends('suppinfo_id.pricelist_ids', 'min_quantity', 'validity_date')
    def _is_active_line(self):
        for rec in self:
            rec.active_line = rec.is_active()

    @api.multi
    def is_active(self, check_force_inactive=True):
        self.ensure_one()
        context = self.env.context or {}
        reference_date = context.get('date') or time.strftime('%Y-%m-%d')
        active = True
        list_line = []
        if check_force_inactive and self.force_inactive:
            return False
        for item in self.suppinfo_id.pricelist_ids:
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
    _inherit = 'product.pricelist'

    @api.model
    def _price_rule_get_multi(self, pricelist, products_by_qty_by_partner):
        """
        Price list applied is the one from the product.supplierinfo with the highest priority
        (sequence closest to 1), which is valid, respect the minimum quantity and has
        the closest validity_date before today
        :param pricelist:
        :param products_by_qty_by_partner:
        :return: result from super, with modified price calculation
        """
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
                        price = False
                        qty_uom_id = context.get('uom') or product.uom_id.id
                        price_uom_id = product.uom_id.id
                        if qty_uom_id != product.uom_id.id:
                            try:
                                product_uom_obj._compute_qty(context['uom'], qty,
                                                             product.uom_id.id or product.uos_id.id)
                            except except_orm:
                                # Ignored - incompatible UoM in context, use default product UoM
                                pass
                        suppinfos = self.find_supplierinfos_for_product(product, partner)
                        valid_pricelists = self.env['pricelist.partnerinfo']
                        price_uom_ids = {}

                        for suppinfo in suppinfos: # we iterate over supplier_info (fourniture achat) because they may be many for one supplier
                            qty_in_seller_uom = qty
                            seller_uom = suppinfo.product_uom.id
                            if qty_uom_id != seller_uom:
                                qty_in_seller_uom = product_uom_obj._compute_qty(qty_uom_id, qty, to_uom_id=seller_uom)
                            price_uom_ids[suppinfo.id] = seller_uom  # stored in a dictionary to be able to retrive the one associated with the choosen supplier_info
                            # we retrieve valid price list = active, min quantity respected  and validity date ok
                            valid_pricelists |= suppinfo.pricelist_ids.filtered(lambda pricelist: not pricelist.force_inactive
                                                                                          and pricelist.active_line
                                                                                          and pricelist.validity_date <= date
                                                                                          and (pricelist.end_validity_date == False
                                                                                               or pricelist.end_validity_date <= date)
                                                                                          and pricelist.min_quantity <= qty_in_seller_uom)
                        # the right pricelist is the one with lower priority and newer validity_date
                        good_pricelist = valid_pricelists and valid_pricelists.sorted(key=lambda plist: plist.validity_date, reverse=True).sorted(key = lambda plist: plist.sequence)[0] or False
                        price = good_pricelist and good_pricelist.price or 0.0
                        price_uom_id = price_uom_ids and price_uom_ids[good_pricelist.suppinfo_id.id] or False
                        break

                if price_uom_id and qty_uom_id and rule_id:
                    price = product_uom_obj._compute_price(price_uom_id, price, qty_uom_id)
                    results[product.id] = (price, rule_id)
        return results


class procurement_order(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _get_po_line_values_from_proc(self, procurement, partner, company, schedule_date):
        date = fields.Date.to_string(schedule_date)
        result = super(procurement_order, self.with_context(date=date))._get_po_line_values_from_proc(procurement,
                                                                                                      partner, company,
                                                                                                      schedule_date)
        return result
