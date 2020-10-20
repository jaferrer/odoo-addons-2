# -*- coding: utf8 -*-
#
#    Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api, fields
from openerp.osv import fields as old_api_fields
from openerp.tools import float_round


class PurchaseOrderLinePlanningImproved(models.Model):
    _inherit = 'purchase.order.line'

    covering_state = fields.Selection([
        ('all_covered', u"All Need Covered"),
        ('coverage_computed', u"Computed Coverage"),
        ('unknown_coverage', u"Not Calculated State")
    ], string=u"Covered State", default='unknown_coverage', required=True, readonly=True)

    @api.cr_uid_ids_context
    def _get_remaining_qty(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if 'no_recompute_rar' not in context:
            for line in self.browse(cr, uid, ids, context=context):
                res[line.id] = 0
                if line.product_id and line.product_id.type != 'service':
                    remaining_qty_pol_uom = line.compute_remaining_qty()['remaining_qty_pol_uom']
                    res[line.id] = float_round(remaining_qty_pol_uom, precision_rounding=line.product_uom.rounding)
                if res[line.id] == line.remaining_qty:
                    del res[line.id]
        return res

    @api.multi
    def get_running_moves_for_line(self):
        self.ensure_one()
        return self.env['stock.move'].search([('purchase_line_id', '=', self.id),
                                              ('state', 'not in', ['done', 'cancel']),
                                              ('origin_returned_move_id', '=', False)], order='product_qty')

    @api.multi
    def compute_remaining_qty(self, line_uom_id=False):
        self.ensure_one()
        delivered_qty_pol_uom = 0
        remaining_qty_pol_uom = 0
        returned_qty_pol_uom = 0
        qty_running_pol_uom = 0
        line_uom = line_uom_id and self.env['product.uom'].search([('id', '=', line_uom_id)]) or self.product_uom
        running_moves = self.env['stock.move']
        if self.product_id and self.product_id.type != 'service':
            self.env.cr.execute("""SELECT sum(sm.product_qty)
FROM purchase_order_line pol
LEFT JOIN stock_move sm ON sm.purchase_line_id = pol.id AND
sm.state = 'done' AND
sm.origin_returned_move_id IS NULL
WHERE pol.id = %s""", (self.id,))
            delivered_qty = self.env.cr.fetchall()[0][0] or 0
            delivered_qty_pol_uom = self.env['product.uom']._compute_qty(self.product_id.uom_id.id,
                                                                         delivered_qty,
                                                                         self.product_uom.id)
            self.env.cr.execute("""SELECT sum(sm.product_qty)
FROM purchase_order_line pol
LEFT JOIN stock_move sm ON sm.purchase_line_id = pol.id AND
sm.state = 'done' AND
sm.origin_returned_move_id IS NOT NULL
WHERE pol.id = %s""", (self.id,))
            returned_qty = self.env.cr.fetchall()[0][0] or 0
            returned_qty_pol_uom = self.env['product.uom']._compute_qty(self.product_id.uom_id.id,
                                                                        returned_qty,
                                                                        self.product_uom.id)
            running_moves = self.get_running_moves_for_line()
            qty_running_product_uom = sum(x.product_qty for x in running_moves)
            qty_running_pol_uom = self.env['product.uom']._compute_qty(self.product_id.uom_id.id,
                                                                       qty_running_product_uom,
                                                                       line_uom.id)
            delivered_qty_pol_uom = delivered_qty_pol_uom
            remaining_qty_pol_uom = self.product_qty - delivered_qty_pol_uom + returned_qty_pol_uom
        return {'delivered_qty_pol_uom': delivered_qty_pol_uom,
                'remaining_qty_pol_uom': remaining_qty_pol_uom,
                'returned_qty_pol_uom': returned_qty_pol_uom,
                'qty_running_pol_uom': qty_running_pol_uom,
                'running_moves': running_moves}

    @api.cr_uid_ids_context
    def _get_purchase_order_lines(self, cr, uid, ids, context=None):
        res = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.purchase_line_id:
                res.add(move.purchase_line_id.id)
        return list(res)

    _columns = {
        'remaining_qty': old_api_fields.function(
            _get_remaining_qty, type="float", copy=False, digits_compute=dp.get_precision('Product Unit of Measure'),
            store={
                'purchase.order.line': (lambda self, cr, uid, ids, ctx: ids, ['product_qty'], 20),
                'stock.move': (_get_purchase_order_lines, ['purchase_line_id', 'product_uom_qty',
                                                           'product_uom', 'state', 'origin_returned_move_id'], 20)},
            string="Remaining quantity", help="Quantity not yet delivered by the supplier")}
