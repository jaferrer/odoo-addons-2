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
        for rec in self:
            in_invoices = rec.env['account.invoice.line'].search([('invoice_id.state','in',['open','paid']),
                                                                  ('invoice_id.type','=','in_invoice'),
                                                                  ('invoice_id.partner_id','=',rec.id)])
            in_refunds = rec.env['account.invoice.line'].search([('invoice_id.state','in',['open','paid']),
                                                                 ('invoice_id.type','=','in_refund'),
                                                                 ('invoice_id.partner_id','=',rec.id)])
            total_invoice = 0
            total_refund = 0
            for line in in_invoices:
                total_invoice += line.price_subtotal
            for line in in_refunds:
                total_refund += line.price_subtotal
            rec.total_purchase = total_invoice - total_refund

    @api.multi
    def _compute_total_sale_supplier(self):
        for rec in self:
            out_invoices = rec.env['account.invoice.line'].search([('invoice_id.type','=','out_invoice'),
                                                                   ('invoice_id.state','in',['open','paid']),
                                                                   ('product_id.product_tmpl_id.seller_id','=',rec.id)])
            out_refunds = rec.env['account.invoice.line'].search([('invoice_id.type','=','out_refund'),
                                                                  ('invoice_id.state','in',['open','paid']),
                                                                  ('product_id.product_tmpl_id.seller_id','=',rec.id)])
            total_invoice = 0
            total_refund = 0
            for line in out_invoices:
                total_invoice += line.price_subtotal
            for line in out_refunds:
                total_refund += line.price_subtotal
            rec.total_sale_supplier = total_invoice - total_refund

    @api.multi
    def _compute_total_purchase_order(self):
        for rec in self:
            orders = rec.env['purchase.order.line'].search(
                        [('order_id.state','in',['purchase', 'picking_in_progress', 'to approve', 'picking_done',
                                                 'except_picking', 'except_invoice']),
                         ('partner_id','=',rec.id)])
            total_orders = 0
            for line in orders:
                total_orders += line.price_subtotal
            rec.total_purchase_order = total_orders
