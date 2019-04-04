# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import openerp.addons.decimal_precision as dp
from openerp.osv import fields as old_api_fields
from openerp import models, fields, api


class SaleOrderImproved(models.Model):
    _inherit = 'sale.order'
    _order = 'date_order desc, id desc'

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.order_line:
                # We have to overwrite this function to compute last value of price subtotal
                # (this field is now pseudo-store)
                val1 += line._amount_line(None, None).get(line.id, 0)
                val += self._amount_line_tax(cr, uid, line, context=context)
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res

    def _amount_all_improved(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for order_id in ids:
            order = self.pool.get('sale.order').browse(cr, uid, order_id, context=context)
            target_data = self.pool.get('sale.order')._amount_all(cr, uid, order_id, field_name, arg, context=context)
            order_data = {'amount_tax': order.amount_tax,
                          'amount_untaxed': order.amount_untaxed,
                          'amount_total': order.amount_total}
            if order_data != target_data.get(order_id):
                result[order_id] = target_data.get(order_id)
        return result

    def _get_order_improved(self, cr, uid, ids, context=None):
        result = self.pool.get('sale.order')._get_order(cr, uid, ids, context=context)
        return result

    _columns = {
        'amount_untaxed': old_api_fields.function(_amount_all_improved, digits_compute=dp.get_precision('Account'),
                                                  string='Untaxed Amount', store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order_improved, ['product_qty', 'taxes_id',
                                                          'product_uom', 'product_id',
                                                          'price_unit', 'order_id'], 10),
            }, multi="sums", help="The amount without tax", track_visibility='always'),
        'amount_tax': old_api_fields.function(_amount_all_improved, digits_compute=dp.get_precision('Account'),
                                              string='Taxes',
                                              store={
                                                  'sale.order': (
                                                      lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                                                  'sale.order.line': (_get_order_improved, ['product_qty', 'taxes_id',
                                                                                            'product_uom', 'product_id',
                                                                                            'price_unit', 'order_id'],
                                                                      10),
                                              }, multi="sums", help="The tax amount"),
        'amount_total': old_api_fields.function(_amount_all_improved, digits_compute=dp.get_precision('Account'),
                                                string='Total', store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order_improved, ['product_qty', 'taxes_id',
                                                          'product_uom', 'product_id',
                                                          'price_unit', 'order_id'], 10),
            }, multi="sums", help="The total amount")
    }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    price_subtotal_store = fields.Float(compute='_compute_price_subtotal', store=True)
    price_subtotal = fields.Float(related='price_subtotal_store', store=False)

    @api.depends('product_uom_qty', 'price_unit', 'discount')
    @api.multi
    def _compute_price_subtotal(self):
        for rec in self:
            rec.price_subtotal_store = rec.product_uom_qty * rec.price_unit * (1 - float(rec.discount) / 100)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        super_result = super(SaleOrderLine, self).read(fields=fields, load=load)
        if 'tax_id' in fields:
            taxes_names_dict = {tax_id: name for (tax_id, name) in self.env['account.tax'].search([]).name_get()}
            result = []
            for res in super_result:
                res['tax_id__display'] = ', '.join([taxes_names_dict[tax.id] for tax in self.browse(res['id']).tax_id])
                result += [res]
            return result
        return super_result
