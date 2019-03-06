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

from openerp import models, api
from openerp.osv import fields as old_api_fields
from openerp.tools import float_round


class PurchaseOrderLinePlanningImproved(models.Model):
    _inherit = 'purchase.order.line'

    @api.cr_uid_ids_context
    def _get_remaining_qty(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            remaining_qty = 0
            if line.product_id and line.product_id.type != 'service':
                delivered_qty = sum([self.pool.get('product.uom').
                                    _compute_qty(cr, uid, move.product_uom.id,
                                                 move.product_uom_qty, line.product_uom.id)
                                     for move in line.move_ids if move.state == 'done'])
                remaining_qty = float_round(line.product_qty - delivered_qty,
                                            precision_rounding=line.product_uom.rounding)
            res[line.id] = remaining_qty
            if res[line.id] == line.remaining_qty:
                del res[line.id]
        return res

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
                                                           'product_uom', 'state'], 20)},
            string="Remaining quantity", help="Quantity not yet delivered by the supplier")}
