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


class PurchasePlanning(models.Model):
    _name = 'purchase.planning'
    _description = "Purchase Planning"

    def _default_suggest_qty(self):
        return self.suggest_qty

    name = fields.Char(u"Name")
    product_id = fields.Many2one('product.product', u"Product", required=True, readonly=True)
    stock_qty = fields.Float(u"Quantity in stock", related='product_id.qty_available', readonly=True)
    forecast_qty = fields.Float(u"Forecast quantity", related='product_id.virtual_available', readonly=True)
    supplier_id = fields.Many2one('product.supplierinfo', u"Supplier")
    min_qty = fields.Float(u"Minimum quantity", related='supplier_id.min_qty', readonly=True)
    packaging_qty = fields.Float(u"Packaging quantity", related='supplier_id.packaging_qty', readonly=True)
    delay = fields.Integer(u"Delivery Lead Time", related='supplier_id.delay', readonly=True)
    period_id = fields.Many2one('period.planning', u"Period", required=True, readonly=True)
    suggest_qty = fields.Float(u"Suggest quantity", compute='_compute_suggest_qty', readonly=True)
    retained_qty_with_constraint = fields.Float(u"Retained quantity with constraint", compute='_onchange_retained_qty')
    retained_qty = fields.Float(u"Retained quantity")
    suggest_qty_no_constraint = fields.Float(u"Suggest quantity without constraint", readonly=True)
    final_qty = fields.Float(u"Final quantity")
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id')
    count_purchase_order = fields.Integer("Count purchase order", compute='_compute_count_purchase_order')
    state = fields.Selection([
        ('draft', u"Draft"),
        ('confirm', u"Confirmed"),
        ('lock', u"Locked"),
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
        for rec in self:
            if rec.period_id.purchase_state == "confirm" and not vals.get('state'):
                vals['state'] = "draft"
                rec.period_id.cancel_po()
            elif rec.period_id.purchase_state == "draft":
                vals['state'] = "confirm"
        super(PurchasePlanning, self).write(vals)

    @api.multi
    def _compute_purchase_order_line_id(self):
        group_id = self.period_id.purchase_group_id
        pol = self.env['purchase.order'].search([('group_id', '=', group_id.id)]).mapped('order_line')
        self.purchase_order_line_ids = pol.filtered(lambda l: l.product_id == self.product_id)

    @api.multi
    def _compute_count_purchase_order(self):
        for rec in self:
            po = self.env['purchase.order.line'].search([('product_id', '=', rec.product_id.id)]).filtered(
                lambda l: l.order_id.group_id == rec.period_id.purchase_group_id).mapped('order_id')
            rec.count_purchase_order = len(po)

    @api.onchange('supplier_id')
    def _onchange_supplier_id(self):
        self._compute_suggest_qty()

    @api.onchange('retained_qty', 'packaging_qty', 'min_qty')
    def _onchange_retained_qty(self):
        if self.packaging_qty != 0:
            self.retained_qty_with_constraint = self.packaging_qty * ceil(
                max(self.min_qty, self.retained_qty) / self.packaging_qty)
        else:
            self.retained_qty_with_constraint = max(self.min_qty, self.retained_qty)

    @api.multi
    def _compute_suggest_qty(self):
        for rec in self:
            if not rec.suggest_qty_no_constraint or rec.suggest_qty_no_constraint == 0:
                start_date, end_date = rec.period_id.season_id._get_duration(rec.period_id.year_id.name - 1)
                purchase_order_lines = self.env['purchase.order.line'].search([
                    ('date_planned', '>=', start_date),
                    ('date_planned', '<=', end_date),
                    ('state', '=', 'done'),
                    ('product_id', '=', rec.product_id.id),
                ])
                past_qty = sum(purchase_order_lines.mapped('product_uom_qty'))
            else:
                past_qty = rec.suggest_qty_no_constraint
            if rec.packaging_qty != 0:
                rec.suggest_qty = rec.packaging_qty * ceil(max(rec.min_qty, past_qty) / rec.packaging_qty)
            else:
                rec.suggest_qty = max(rec.min_qty, past_qty)

    @api.multi
    def see_purchase_order(self):
        self.ensure_one()
        po = self.env['purchase.order.line'].search([('product_id', '=', self.product_id.id)]).filtered(
            lambda l: l.order_id.group_id == self.period_id.purchase_group_id).mapped('order_id')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Order',
            'res_model': 'purchase.order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'context': self.env.context,
            'domain': [('id', 'in', po.ids)],
            'target': 'current',
        }
