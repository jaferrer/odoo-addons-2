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

from openerp import models, fields, api
from openerp.tools.float_utils import float_compare


class ProcurementOrderPurchaseJustInTime(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def propagate_cancel(self, procurement):

        """
        Improves the original propagate_cancel function. If the corresponding purchase order is draft, it eventually
        cancels and/or deletes the purchase order line and the purchase order.
        """

        result = None
        to_delete = False
        if procurement.rule_id.action == 'buy' and procurement.purchase_line_id:
            # Canceling a confirmed procurement order if needed
            line = procurement.purchase_line_id
            order = line.order_id
            total_need = 0
            for order_line in order.order_line:
                total_need += sum(
                    [x.product_qty for x in order_line.procurement_ids if x.product_id == line.product_id
                     and x != procurement and x.state != 'cancel'])
            if float_compare(total_need, 0.0, precision_rounding=procurement.product_uom.rounding) != 0:
                total_need = self.with_context(cancelling_active_proc=True). \
                    _calc_new_qty_price(procurement)[0]
            # Considering the case of different lines with same product in one order
            total_need = total_need - sum([l.product_qty for l in order.order_line if l != line and
                                           l.product_id == line.product_id])
            if procurement.purchase_line_id.order_id.state not in ['draft', 'cancel', 'done']:
                opmsg_reduce_qty = total_need
                if float_compare(total_need, 0.0, precision_rounding=procurement.product_uom.rounding) == 0:
                    to_delete = True
                line = procurement.purchase_line_id
                procurement.purchase_line_id.write({'opmsg_reduce_qty': opmsg_reduce_qty,
                                                    'to_delete': to_delete})
                vals_to_write = {'purchase_id': False, 'purchase_line_id': False}
                if [x for x in procurement.move_ids if x.state == 'done']:
                    vals_to_write['product_qty'] = sum([x.product_qty for x in procurement.move_ids if x.state == 'done'])
                if line:
                    moves_to_unlink = line.move_ids.filtered(lambda x: x.state not in ['done', 'cancel'] and
                                                                       x.procurement_id == procurement)
                    new_moves = moves_to_unlink.copy({'state': 'draft', 'procurement_id': False, 'move_dest_id': False})
                    new_moves.write({'purchase_line_id': line.id})
                    moves_to_unlink.action_cancel()
                    moves_to_unlink.unlink()
                    new_moves.action_confirm()
                    new_moves.action_assign()
                procurement.check()
                procurement.write(vals_to_write)
            else:
                result = super(ProcurementOrderPurchaseJustInTime,
                               self.with_context(cancelling_active_proc=True)).propagate_cancel(procurement)
        else:
            result = super(ProcurementOrderPurchaseJustInTime, self).propagate_cancel(procurement)
        return result