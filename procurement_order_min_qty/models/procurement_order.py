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

from odoo import models, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def make_po(self):
        """ Redefine procurement.order.make_po method from purchase/models/purchase.py l 1057

        Take into account the min_qty in the product.supplierinfo, in order to avoid ordering not enough of a product
        """
        cache = {}
        res = []
        for procurement in self:
            suppliers = procurement.product_id.seller_ids\
                .filtered(lambda r: (not r.company_id or r.company_id == procurement.company_id) and
                                    (not r.product_id or r.product_id == procurement.product_id))
            if not suppliers:
                procurement.message_post(
                    body=_('No vendor associated to product %s. Please set one to fix this procurement.') %
                    procurement.product_id.name)
                continue
            supplier = procurement._make_po_select_supplier(suppliers)
            partner = supplier.name

            domain = procurement._make_po_get_domain(partner)

            if domain in cache:
                po = cache[domain]
            else:
                po = self.env['purchase.order'].search([dom for dom in domain])
                po = po[0] if po else False
                cache[domain] = po
            if not po:
                vals = procurement._prepare_purchase_order(partner)
                po = self.env['purchase.order'].create(vals)
                name = (procurement.group_id and (procurement.group_id.name + ":") or "") + \
                       (procurement.name != "/" and procurement.name or "")
                message = _("This purchase order has been created from: "
                            "<a href=# data-oe-model=procurement.order data-oe-id=%d>%s</a>") % (procurement.id, name)
                po.message_post(body=message)
                cache[domain] = po
            elif not po.origin or procurement.origin not in po.origin.split(', '):
                # Keep track of all procurements
                if po.origin:
                    if procurement.origin:
                        po.write({'origin': po.origin + ', ' + procurement.origin})
                    else:
                        po.write({'origin': po.origin})
                else:
                    po.write({'origin': procurement.origin})
                name = (self.group_id and (self.group_id.name + ":") or "") + (self.name != "/" and self.name or "")
                message = _("This purchase order has been modified from: "
                            "<a href=# data-oe-model=procurement.order data-oe-id=%d>%s</a>") % (procurement.id, name)
                po.message_post(body=message)
            if po:
                res += [procurement.id]

            # Create Line
            po_line = False
            for line in po.order_line:
                # 1/ If there is a corresponding line with some procurement.order already linked, add this to it
                if line.product_id == procurement.product_id \
                        and line.product_uom == procurement.product_id.uom_po_id \
                        and line.procurement_ids:

                    res = self._prepare_update_purchase_order_line(line, partner, po, procurement)
                    po_line = line.write(res)
                    break
            # 2/ Else, create a new purchase.order.line
            if not po_line:
                vals = procurement._prepare_purchase_order_line(po, supplier)
                self.env['purchase.order.line'].create(vals)
        return res

    def _prepare_update_purchase_order_line(self, line, partner, po, procurement):
        """ Return a dict of values to refresh the number of product, price, etc of a purchase.order.line, to take into
        account a new procurement.order

        We only add procurement to a line already having procurement orders.
        This way, we can now exactly know what quantity of the product we really want, by summing each
        of these line procurement's quantity, then completing, if needed, to reach product.supplierinfo
        threshold.
        If the line was manually created and filled, we don't have a simple way to know how much product is
        really needed, and how much is there to reach the product.supplierinfo min_qty threshold. So, we won't
        add any procurement to this kind of lines, and will skip it

        :param line: the purchase.order.line that must be updated
        :param po: the whole associated purchase.order
        :param procurement: procurement.order to add to this line
        """
        # 1.1/ Estimate the total needed quantity
        procurement_uom_po_qty = sum(
            proc.product_uom._compute_quantity(proc.product_qty, proc.product_id.uom_po_id)
            for proc in line.procurement_ids | procurement
        )

        # 1.2/ Find the closest product.supplierinfo rule
        seller = procurement.product_id._select_closest_seller(
            partner_id=partner,
            quantity=procurement_uom_po_qty,
            date=po.date_order and po.date_order[:10],
            uom_id=procurement.product_id.uom_po_id)

        # 1.3/ If we need less than the min_qty threshold, qty is readjusted
        procurement_uom_po_qty = max(procurement_uom_po_qty, seller.min_qty)

        # 1.4/ Compute the unit price that we'll chose
        price_unit = self.env['account.tax']._fix_tax_included_price_company(
            seller.price,
            line.product_id.supplier_taxes_id,
            line.taxes_id, self.company_id) \
            if seller else 0.0
        if price_unit and seller and po.currency_id and seller.currency_id != po.currency_id:
            price_unit = seller.currency_id.compute(price_unit, po.currency_id)

        # 1.5/ Return the new values
        return {
            'product_qty': procurement_uom_po_qty,
            'price_unit': price_unit,
            'procurement_ids': [(4, procurement.id)]
        }

    @api.multi
    def _prepare_purchase_order_line(self, po, supplier):
        """ Return dict of values to create a new purchase.order.line """
        self.ensure_one()

        # 2.1/ Estimate the needed quantity
        procurement_uom_po_qty = self.product_uom._compute_quantity(self.product_qty, self.product_id.uom_po_id)

        # 2.2/ Find the closest product.supplierinfo
        seller = self.product_id.with_context(force_company=self.company_id.id)._select_closest_seller(
            partner_id=supplier.name,
            quantity=procurement_uom_po_qty,
            date=po.date_order and po.date_order[:10],
            uom_id=self.product_id.uom_po_id)

        # 1.3/ If we need less than the min_qty threshold, qty is readjusted
        procurement_uom_po_qty = max(procurement_uom_po_qty, seller.min_qty)

        # 1.4/ Calculate taxes, unit prices, etc...
        taxes = self.product_id.supplier_taxes_id
        fpos = po.fiscal_position_id
        taxes_id = fpos.map_tax(taxes) if fpos else taxes
        if taxes_id:
            taxes_id = taxes_id.filtered(lambda x: x.company_id.id == self.company_id.id)

        price_unit = self.env['account.tax']._fix_tax_included_price_company(
            seller.price,
            self.product_id.supplier_taxes_id,
            taxes_id, self.company_id) \
            if seller else 0.0
        if price_unit and seller and po.currency_id and seller.currency_id != po.currency_id:
            price_unit = seller.currency_id.compute(price_unit, po.currency_id)

        product_lang = self.product_id.with_context({
            'lang': supplier.name.lang,
            'partner_id': supplier.name.id,
        })
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase

        date_planned = self.env['purchase.order.line']._get_date_planned(seller, po=po)\
            .strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        # 1.5/ Return values of the new line
        return {
            'name': name,
            'product_qty': procurement_uom_po_qty,
            'product_id': self.product_id.id,
            'product_uom': self.product_id.uom_po_id.id,
            'price_unit': price_unit,
            'date_planned': date_planned,
            'taxes_id': [(6, 0, taxes_id.ids)],
            'procurement_ids': [(4, self.id)],
            'order_id': po.id,
        }
