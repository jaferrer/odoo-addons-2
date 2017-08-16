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

from openerp import models, fields, api, _
from openerp.exceptions import ValidationError


class SalePurchaseCommissionProductTemplate(models.Model):
    _inherit = 'product.template'

    commission_rate = fields.Float(string=u"Commission Rate (%)")


class SalePurchaseCommissionProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def get_commissions_for_product(self, date, customer=None, force_supplier=None):
        self.ensure_one()
        commission_obj = self.env['sale.commission']
        domain = commission_obj.get_domain_date_validity(date)
        domain += [('commission_rate', '>', 0),
                   ('supplier_id', '!=', False),
                   ('commission_product_id', '!=', False)]
        done_supplier_ids = []
        if force_supplier:
            domain += [('supplier_id', '=', force_supplier.id)]
        commissions = commission_obj.search(domain + [('sold_product_id', '=', self.id)])
        for commission in commissions:
            if commission.supplier_id.id not in done_supplier_ids:
                done_supplier_ids += [commission.supplier_id.id]
        if self.categ_id:
            commissions += commissions.search(domain + [('categ_id', '=', self.categ_id.id),
                                                        ('supplier_id', 'not in', done_supplier_ids)])
        if customer:
            commissions += commissions.search(domain + [('partner_id', '=', customer.id),
                                                        ('supplier_id', 'not in', done_supplier_ids)])
        return commissions


class SalePurchaseCommission(models.Model):
    _name = 'sale.commission'
    _order = 'date_end desc, date_begin desc, id desc'

    supplier_id = fields.Many2one('res.partner', string=u"Business provider", domain=[('supplier', '=', True)],
                                  required=True)
    partner_id = fields.Many2one('res.partner', string=u"Customer", domain=[('customer', '=', True)])
    categ_id = fields.Many2one('product.category', string=u"Product Category")
    sold_product_id = fields.Many2one('product.product', string=u"Sold product",
                                      domain=[('sale_ok', '=', True)])
    commission_product_id = fields.Many2one('product.product', string=u"Commission product",
                                            domain=[('purchase_ok', '=', True)], required=True)
    commission_rate = fields.Float(string=u"Commission Rate (%)",
                                   related='commission_product_id.commission_rate', store=True, readonly=True)
    date_begin = fields.Date(string=u"Date begin")
    date_end = fields.Date(string=u"Date end")

    @api.constrains('partner_id', 'categ_id', 'sold_product_id')
    def set_commission_constrains(self):
        for rec in self:
            if not rec.partner_id and not rec.categ_id and not rec.sold_product_id:
                raise ValidationError(_(u"You must specify at least one customer, one category or one "
                                        u"product"))

    @api.model
    def get_domain_date_validity(self, date):
        return ['&',
                '|', ('date_begin', '=', False), ('date_begin', '<', date),
                '|', ('date_end', '=', False), ('date_end', '>', date)]


class SaleCommissionSaleOrder(models.Model):
    _inherit = 'sale.order'

    supplier_id = fields.Many2one('res.partner', string=u"Business provider", domain=[('supplier', '=', True)])
    commission_product_id = fields.Many2one('product.product', string=u"Commission product",
                                            domain=[('purchase_ok', '=', True)])
    commission_rate = fields.Float(string=u"Commission Rate (%)",
                                   related='commission_product_id.commission_rate', store=True, readonly=True)

    @api.multi
    def create_commission_lines(self):
        for rec in self:
            for line in rec.order_line:
                supplier = line.supplier_id or rec.supplier_id
                commission_product = line.supplier_id and line.commission_product_id or \
                                     rec.supplier_id and rec.commission_product_id
                commmission_rate = line.supplier_id and line.commission_rate or \
                                   rec.supplier_id and rec.commission_rate
                if supplier and commission_product and commmission_rate:
                    purchase_order = self.env['purchase.order'].search([('partner_id', '=', supplier.id),
                                                                        ('state', '=', 'draft')], limit=1)
                    if not purchase_order:
                        purchase_order = self.env['purchase.order'].create({'partner_id': supplier.id})
                    self.env['purchase.order.line'].create({
                        'order_id': purchase_order.id,
                        'product_id': commission_product.id,
                        'name': _(u"Commission for product %s in sale order %s") %
                                (line.product_id.name, rec.name),
                        'price_unit': float(line.price_subtotal * commmission_rate) / 100,
                        'product_qty': 1,
                        'product_uom': commission_product.uom_id.id,
                        'date_planned': fields.Datetime.now(),
                    })

    @api.multi
    def action_confirm(self):
        result = super(SaleCommissionSaleOrder, self).action_confirm()
        self.create_commission_lines()
        return result


class SaleCommissionSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    supplier_id = fields.Many2one('res.partner', string=u"Business provider", domain=[('supplier', '=', True)])
    commission_product_id = fields.Many2one('product.product', string=u"Commission product",
                                            domain=[('purchase_ok', '=', True)])
    commission_rate = fields.Float(string=u"Commission Rate (%)",
                                   related='commission_product_id.commission_rate', store=True, readonly=True)

    @api.model
    def create(self, vals):
        if self.env.context.get('fill_commissions_automatically') and \
                vals.get('order_id') and vals.get('product_id') and \
                not vals.get('supplier_id') and not vals.get('commission_rate'):
            order = self.env['sale.order'].browse(vals['order_id'])
            product = self.env['product.product'].browse(vals['product_id'])
            date_today = fields.Date.today()
            force_supplier = order.supplier_id
            commission_lines = product.get_commissions_for_product(date_today, customer=order.partner_id,
                                                                   force_supplier=force_supplier)
            if commission_lines:
                vals['supplier_id'] = commission_lines[0].supplier_id.id
                vals['commission_product_id'] = commission_lines[0].commission_product_id.id
        return super(SaleCommissionSaleOrderLine, self).create(vals)

    @api.onchange('product_id')
    def onchange_commission_data(self):
        for rec in self:
            if rec.product_id and rec.order_id:
                date_today = fields.Date.today()
                force_supplier = rec.order_id.supplier_id
                commission_lines = rec.product_id. \
                    get_commissions_for_product(date_today, customer=rec.order_id.partner_id,
                                                force_supplier=force_supplier)
                if commission_lines:
                    rec.supplier_id = commission_lines[0].supplier_id
                    rec.commission_product_id = commission_lines[0].commission_product_id
