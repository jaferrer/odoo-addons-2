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

from openerp import models, fields, exceptions, api, _
from openerp.tools import float_compare, float_round
from datetime import datetime
from dateutil import relativedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ReceptionByOrderStockPackOperation(models.Model):
    _inherit = 'stock.pack.operation'

    @api.multi
    def get_list_operations_to_process(self):
        linked_purchase_orders = set([ops.sale_line_id.order_id for ops in self if ops.sale_line_id])
        if len(linked_purchase_orders) > 1:
            raise exceptions.except_orm(_("Error!"), _("Impossible to receive two different purchase orders at the "
                                                       "same time. Please check your packing operationd and retry."))
        if any([ops.sale_line_id and ops.product_id != ops.sale_line_id.product_id for ops in self]):
            raise exceptions.except_orm(_("Error!"), _("Impossible to receive a product on a purchase order line "
                                                       "linked to another product. Please check your packing "
                                                       "operations and retry."))
        # First operation should be the ones which are linked to a purchase_order_line
        operations_with_sale_lines = self.search([('id', 'in', self.ids), ('sale_line_id', '!=', False)])
        if operations_with_sale_lines:
            operations_without_sale_lines = self.search([('id', 'in', self.ids),
                                                         ('id', 'not in', operations_with_sale_lines.ids)])
            return [operations_with_sale_lines, operations_without_sale_lines]
        else:
            return super(ReceptionByOrderStockPackOperation, self).get_list_operations_to_process()

    @api.multi
    def _sort_operations_for_transfer_value(self):
        return (self.sale_line_id and -16 or 0) + super(ReceptionByOrderStockPackOperation, self). \
            _sort_operations_for_transfer_value()


class ExpeditionByOrderLinePicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _create_link_for_product(self, prod2move_ids, operation_id, product_id, qty):
        '''method that creates the link between a given operation and move(s) of given product, for the given quantity.
        Returns True if it was possible to create links for the requested quantity (False if there was not enough quantity on stock moves)'''
        op_sol_id = self.env['stock.pack.operation'].search([('id', '=', operation_id)]) \
            .read(['sale_line_id'], load=False)[0]['sale_line_id']
        if not op_sol_id:
            return super(ExpeditionByOrderLinePicking, self)._create_link_for_product(prod2move_ids, operation_id,
                                                                                      product_id, qty)

        qty_to_assign = qty
        product = self.env['product.product'].browse([product_id])
        rounding = product.uom_id.rounding
        qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
        if prod2move_ids.get(product_id):
            while prod2move_ids[product_id] and qtyassign_cmp > 0:
                i = 0
                for move_data in prod2move_ids[product_id]:
                    if move_data['move']['sale_line_id'] == op_sol_id:
                        qty_on_link, prod2move_ids = self._create_link_for_index(
                            prod2move_ids, operation_id, i, product_id, qty_to_assign, quant_id=False)
                        qty_to_assign -= qty_on_link
                        qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
                        break
                    else:
                        i += 1
                else:
                    break
        result_comp = qtyassign_cmp == 0
        return result_comp, prod2move_ids

    @api.model
    def _create_prod2move_ids(self, picking_id):
        prod2move_ids = {}
        self.env.cr.execute(
            """
SELECT
  id,
  product_qty,
  product_id,
  sale_line_id,
  (CASE WHEN sm.state = 'assigned'
    THEN -2
   ELSE 0 END) + (CASE WHEN sm.partially_available
    THEN -1
                  ELSE 0 END) AS poids
FROM stock_move sm
WHERE sm.picking_id = %s AND sm.state NOT IN ('done', 'cancel') AND sm.sale_line_id IS NOT NULL
ORDER BY poids ASC,""" + self.pool.get('stock.move')._order + """
                    """, (picking_id,)
        )
        res = self.env.cr.fetchall()
        if not res:
            return super(ExpeditionByOrderLinePicking, self)._create_prod2move_ids(picking_id)
        for move in res:
            if not prod2move_ids.get(move[2]):
                prod2move_ids[move[2]] = [
                    {'move': {'id': move[0],
                              'sale_line_id': move[3] or False},
                     'remaining_qty': move[1]}]
            else:
                prod2move_ids[move[2]].append(
                    {'move': {'id': move[0],
                              'sale_line_id': move[3] or False},
                     'remaining_qty': move[1]})
        return prod2move_ids

    @api.model
    def add_packop_values(self, vals, prevals):
        move_with_sale_lines = [x for x in self.move_lines if
                                x.state not in ('done', 'cancel') and x.sale_line_id]
        if not move_with_sale_lines:
            return super(ExpeditionByOrderLinePicking, self).add_packop_values(vals, prevals)

        processed_sale_lines = set()
        for move in move_with_sale_lines:
            if move.product_id and move.sale_line_id.id not in processed_sale_lines:
                uom = move.sale_line_id.product_uom
                sum_quantities_moves_on_line = sum([sm.product_qty for sm in move_with_sale_lines if
                                                    sm.sale_line_id == move.sale_line_id and
                                                    sm.product_id == move.product_id])
                sum_quantities_moves_on_line = self.env['product.uom']. \
                    _compute_qty(move.product_id.uom_id.id, sum_quantities_moves_on_line, uom.id)
                global_qty_to_remove = sum_quantities_moves_on_line
                prevals_same_uom = [item for item in prevals.get(move.product_id.id, []) if
                                    move.product_uom.id == item['product_uom_id']]
                prevals_different_uom = [item for item in prevals.get(move.product_id.id, []) if
                                         move.product_uom.id != item['product_uom_id']]
                for list_vals in [prevals_same_uom, prevals_different_uom]:
                    for item in list_vals:
                        if float_compare(global_qty_to_remove, 0,
                                         precision_rounding=move.product_id.uom_id.rounding) != 0:
                            qty_to_remove = min(sum_quantities_moves_on_line, self.env['product.uom'].
                                                _compute_qty(item['product_uom_id'], item['product_qty'], uom.id))
                            item['product_qty'] -= qty_to_remove
                            global_qty_to_remove -= qty_to_remove
                dict_to_copy = prevals.get(move.product_id.id, [])
                if dict_to_copy:
                    prevals_sale_line = dict_to_copy[0].copy()
                    prevals_sale_line['sale_line_id'] = move.sale_line_id.id
                    prevals_sale_line['product_qty'] = sum_quantities_moves_on_line
                    prevals_sale_line['product_uom_id'] = uom.id
                    vals += [prevals_sale_line]
                    processed_sale_lines.add(move.sale_line_id.id)
        processed_products = set()
        for move in [x for x in self.move_lines if x.state not in ('done', 'cancel') and not x.sale_line_id]:
            if move.product_id.id not in processed_products:
                for item in prevals.get(move.product_id.id, []):
                    if float_compare(item['product_qty'], 0,
                                     precision_rounding=move.product_id.uom_id.rounding) != 0:
                        vals += [item]
                processed_products.add(move.product_id.id)
        return vals

    @api.model
    def _prepare_values_extra_move(self, op, product, remaining_qty):
        result = super(ExpeditionByOrderLinePicking, self)._prepare_values_extra_move(op, product, remaining_qty)

        sale_line = False

        if op.sale_line_id:
            sale_line = op.sale_line_id
        else:
            picking = self.browse([result['picking_id']])
            order_ids = [move.sale_line_id.order_id.id for move in picking.move_lines if move.sale_line_id]
            corresponding_line = self.env['purchase.order.line'].search([('order_id', 'in', order_ids),
                                                                         ('product_id', '=', result['product_id'])],
                                                                        limit=1)
            if corresponding_line:
                result['sale_line_id'] = corresponding_line.id

            sale_line = corresponding_line or sale_line

        if sale_line:
            price_unit = sale_line.price_unit
            if sale_line.tax_id:
                taxes = sale_line.tax_id.compute_all(price_unit, 1.0, sale_line.product_id,
                                                     sale_line.order_id.partner_id)
                price_unit = taxes['total']
            if sale_line.product_uom.id != sale_line.product_id.uom_id.id:
                price_unit *= sale_line.product_uom.factor / sale_line.product_id.uom_id.factor
            if sale_line.order_id.currency_id.id != sale_line.order_id.company_id.currency_id.id:
                # we don't round the price_unit, as we may want to store the standard price with more digits than
                # allowed by the currency
                price_unit = self.env['res.currency'].compute(sale_line.order_id.currency_id.id,
                                                              sale_line.order_id.company_id.currency_id.id,
                                                              price_unit, round=False)
            new_vals = {
                'date': sale_line.order_id.date_order,
                'date_expected': (datetime.strptime(sale_line.date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
                                  + relativedelta.relativedelta(hours=12)).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'partner_id': sale_line.order_id.partner_id.id,
                'sale_line_id': sale_line.id,
                'price_unit': price_unit,
                'company_id': sale_line.order_id.company_id.id,
                'picking_type_id': op.picking_id.picking_type_id.id,
                'origin': sale_line.order_id.name,
                'route_ids': op.picking_id.picking_type_id.warehouse_id and [
                    (6, 0, [x.id for x in op.picking_id.picking_type_id.warehouse_id.route_ids])] or [],
                'warehouse_id': op.picking_id.picking_type_id.warehouse_id.id,
                'invoice_state': (sale_line.order_id.order_policy == 'picking') and '2binvoiced' or 'none',
            }
            result.update(new_vals)
        return result


class ExpeditionByOrderLineStockMove(models.Model):
    _inherit = 'stock.move'

    sale_line_id = fields.Many2one('sale.order.line', string=u"Sale Order Line", index=True)


class ExpeditionByOrderLineSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    procurement_ids = fields.One2many('procurement.order', 'sale_line_id', readonly=True)
    move_ids = fields.One2many('stock.move', 'sale_line_id', readonly=True)
    remaining_qty = fields.Float(u"Qty Still To Be Sent", compute="_get_remaining_qty", store=True)
    sent_qty = fields.Float(u"Quantity Already Sent", compute="_get_remaining_qty", store=True)

    @api.depends('product_uom_qty', 'move_ids', 'move_ids.product_uom_qty', 'move_ids.product_uom', 'move_ids.state')
    def _get_remaining_qty(self):
        """
        Calculates remaining_qty
        """
        for rec in self:
            remaining_qty = 0
            if rec.product_id and rec.product_id.type != 'service':
                delivered_qty = sum([self.env['product.uom']._compute_qty(move.product_uom.id, move.product_uom_qty,
                                                                          rec.product_uom.id)
                                     for move in rec.move_ids if move.state == 'done'])
                remaining_qty = float_round(rec.product_uom_qty - delivered_qty,
                                            precision_rounding=rec.product_uom.rounding)
            rec.remaining_qty = remaining_qty
            rec.sent_qty = rec.product_uom_qty - remaining_qty


class ExpeditionByOrderLineSaleOrder(models.Model):
    _inherit = 'sale.order'

    lines_display = fields.Selection([('not_null_remaining_quantity', u"Not delivered lines"), ('all', u"All lines")],
                                     string=u"Display", default='not_null_remaining_quantity', required=True,
                                     help=u"Choose whether you want to display all lines or only running ones")
    line_not_null_remaining_qty_ids = fields.One2many('sale.order.line', 'order_id', string=u"Not delivered lines",
                                                      domain=[('remaining_qty', '>', 0)],
                                                      states={'done': [('readonly', True)],
                                                              'cancel': [('readonly', True)]})

    @api.multi
    def toggle_lines_display(self):
        for rec in self:
            if rec.lines_display == 'not_null_remaining_quantity':
                rec.lines_display = 'all'
            else:
                rec.lines_display = 'not_null_remaining_quantity'
