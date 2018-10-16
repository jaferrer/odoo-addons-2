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
from openerp import fields, models, api, _


class res_partner_purchase_supplier_stat(models.Model):
    _inherit = 'res.partner'

    total_purchase = fields.Float("Total Purchases", compute="_compute_total_purchase",
                                  help="Total amount purchased at this supplier")
    total_sale_supplier = fields.Float("Total Sales", compute="_compute_total_sale_supplier",
                                       help="Total amount of this supplier's product sold to customers")
    total_purchase_order = fields.Float("Purchase Orders in Progress", compute="_compute_total_purchase_order",
                                        help="Purchase Orders in Progress",
                                        groups="purchase_viewer.group_purchase_viewer")

    @api.multi
    def _compute_total_purchase(self):
        self.env.cr.execute("""SELECT
  ai.partner_id,
  sum(CASE WHEN ai.type = 'in_invoice'
    THEN ail.price_subtotal
      ELSE -1 * ail.price_subtotal END) AS total_purchase
FROM account_invoice ai
  LEFT JOIN account_invoice_line ail ON ail.invoice_id = ai.id
WHERE ai.partner_id IN %s AND
      ai.type IN ('in_invoice', 'in_refund') AND
      ai.state IN ('open', 'paid')
GROUP BY ai.partner_id""", (tuple(self.ids or [0]),))
        result = self.env.cr.fetchall()
        for rec in self:
            total_purchase = 0
            for item in result:
                if item[0] == rec.id:
                    total_purchase = float(item[1])
                    break
            rec.total_purchase = total_purchase

    @api.multi
    def _compute_total_sale_supplier(self):
        self.env.cr.execute("""SELECT
  pt.seller_id,
  sum(CASE WHEN ai.type = 'out_invoice'
    THEN ail.price_subtotal
      ELSE -1 * ail.price_subtotal END) AS total_sale_supplier
FROM account_invoice ai
  LEFT JOIN account_invoice_line ail ON ail.invoice_id = ai.id
  LEFT JOIN product_product pp ON pp.id = ail.product_id
  LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
WHERE pt.seller_id IN %s AND
      ai.type IN ('out_invoice', 'out_refund') AND
      ai.state IN ('open', 'paid')
GROUP BY pt.seller_id;""", (tuple(self.ids or [0]),))
        result = self.env.cr.fetchall()
        for rec in self:
            total_sale_supplier = 0
            for item in result:
                if item[0] == rec.id:
                    total_sale_supplier = float(item[1])
                    break
            rec.total_sale_supplier = total_sale_supplier

    @api.multi
    def _compute_total_purchase_order(self):
        self.env.cr.execute("""SELECT
  po.partner_id,
  sum(pol.product_qty * pol.price_unit) AS total_purchase_order
FROM purchase_order po
  LEFT JOIN purchase_order_line pol ON pol.order_id = po.id
WHERE po.partner_id IN %s AND
      po.state IN ('approved', 'picking_in_progress', 'confirmed', 'picking_done',
                   'except_picking', 'except_invoice')
GROUP BY po.partner_id""", (tuple(self.ids or [0]),))
        result = self.env.cr.fetchall()
        for rec in self:
            total_purchase_order = 0
            for item in result:
                if item[0] == rec.id:
                    total_purchase_order = float(item[1])
                    break
            rec.total_purchase_order = total_purchase_order
