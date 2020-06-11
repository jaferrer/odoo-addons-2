# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from math import ceil

from odoo import fields, models, api
from odoo.exceptions import UserError


class PurchasePlanning(models.Model):
    _name = 'purchase.planning'
    _description = "Purchase Planning"

    def _default_suggest_qty(self):
        return self.suggest_qty

    name = fields.Char(u"Name")
    product_id = fields.Many2one('product.product', u"Product", required=True, readonly=True)
    stock_qty = fields.Float(u"Quantity in stock", related='product_id.qty_available', readonly=True)
    forecast_qty = fields.Float(u"Forecast quantity", related='product_id.virtual_available', readonly=True)
    supplier_id = fields.Many2one('product.supplierinfo', u"Supplier", required=True)
    min_qty = fields.Float(u"Minimum quantity", related='supplier_id.min_qty', readonly=True)
    packaging_qty = fields.Float(u"Packaging quantity", related='supplier_id.packaging_qty', readonly=True)
    delay = fields.Integer(u"Delivery Lead Time", related='supplier_id.delay', readonly=True)
    period_id = fields.Many2one('period.planning', u"Period", required=True, readonly=True)
    suggest_qty = fields.Float(u"Suggest quantity", compute='_compute_suggest_qty', readonly=True)
    retained_qty = fields.Float(u"Retained quantity")
    suggest_qty_no_constraint = fields.Float(u"Suggest quantity without constraint", compute='_compute_suggest_qty',
                                             readonly=True)
    final_qty = fields.Float(u"Final quantity")
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id')
    purchase_order_line_id = fields.Many2one('purchase.order.line', u"Purchase order line", readonly=True)
    state = fields.Selection([
        ('draft', u"Draft"),
        ('done', u"Done"),
    ], required=True, readonly=True, default='draft')

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            name = "%s from %s %s" % (
                rec.product_id.name, rec.period_id.season_id.name, str(rec.period_id.year_id.name))
            res.append((rec.id, name))
        return res

    @api.multi
    def write(self, vals):
        self._assert_no_update()
        super(PurchasePlanning, self).write(vals)

    @api.multi
    def unlink(self):
        self._assert_no_update()
        super(PurchasePlanning, self).unlink()

    @api.onchange('supplier_id')
    def _onchange_supplier_id(self):
        self._compute_suggest_qty()

    @api.multi
    def _compute_suggest_qty(self):
        for rec in self:
            if not rec.retained_qty:
                start_date, end_date = rec.period_id.season_id._get_duration(rec.year_id.name - 1)
                purchase_order_lines = self.env['purchase.order.line'].search([
                    ('date_planned', '>=', start_date),
                    ('date_planned', '<=', end_date),
                    ('state', '=', 'done'),
                    ('product_id', '=', rec.product_id.id),
                ])
                past_qty = sum(purchase_order_lines.mapped('product_uom_qty'))
            else:
                past_qty = rec.retained_qty
            rec.suggest_qty_no_constraint = past_qty
            if rec.packaging_qty != 0:
                rec.suggest_qty = rec.packaging_qty * ceil(max(rec.min_qty, past_qty) / rec.packaging_qty)
            else:
                rec.suggest_qty = max(rec.min_qty, past_qty)

    @api.multi
    def _assert_no_update(self):
        if not self.env.context.get('force_edit'):
            for rec in self:
                if rec.purchase_order_line_id and rec.purchase_order_line_id.state != 'draft':
                    raise UserError(
                        u"You can't modify forecast when a purchase order is created.")
