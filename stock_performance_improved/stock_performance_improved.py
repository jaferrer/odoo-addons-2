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
import time

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from openerp import fields, models, api, exceptions, _

class stock_picking_performance_improved(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def action_assign(self):
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        Overridden here to improve performance when there are a great number of moves
        @return: True
        """
        for pick in self:
            # First confirm the picking if it is not already
            if pick.state == 'draft':
                self.action_confirm()
            # We get all quants in the picking's source location that are not reserved yet
            quants = self.env['stock.quant'].search([('location_id','child_of',pick.location_id.id),
                                                     ('reservation_id','=',False)])
            # We create a dict with the quantities of each product to reserve
            product_qties = {}
            for quant in quants:
                if quant.product_id in product_qties:
                    product_qties[quant.product_id] += quant.qty
                else:
                    product_qties[quant.product_id] = quant.qty
            # We iterate on each product and quantities to reserve to get the moves to assign
            to_assign_moves = self.env['stock.move']
            for product, qty_todo in product_qties.iteritems():
                # Filter moves on the product
                moves = pick.move_lines.filtered(lambda m: m.product_id == product)
                # Get only the needed number of moves to assign the qty to do and add them to to_assign_moves.
                qty_left = qty_todo
                for move in moves:
                    to_assign_moves = to_assign_moves | move
                    qty_left -= move.product_qty
                    if qty_left <= 0:
                        break
            if not to_assign_moves:
                raise exceptions.except_orm(_('Warning!'), _('Nothing to check the availability for.'))
            to_assign_moves.action_assign()
        return True

    @api.multi
    def rereserve_pick(self):
        """
        This can be used to provide a button that rereserves taking into account the existing pack operations
        Overridden here to limit the number of moves to rereserve
        """
        for pick in self:
            self.rereserve_quants(pick, move_ids = [m.id for m in pick.move_lines if m.availability > 0.0])

    @api.model
    @api.returns('stock.picking')
    def _create_backorder(self, picking, backorder_moves=[]):
        """ Move all done lines into a new picking and keep this one as the backorder. This is the opposite of the
        standard Odoo behaviour in order to gain speed when there are many moves.
        :param picking: A browse record of the picking from which to create a backorder
        :param backorder_moves: Unused
        :rtype : the id of the picking in which the done lines where put
        """
        done_moves = picking.move_lines.filtered(lambda m: m.state in ['done', 'cancel'])
        if done_moves:
            done_picking = picking.copy({
                'name': '/',
                'move_lines': [],
                'pack_operation_ids': [],
                'backorder_id': picking.backorder_id.id,
                'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            })
            done_moves.write({'picking_id': done_picking.id})
            picking.pack_operation_ids.write({'picking_id': done_picking.id})
            picking.message_post(body=_("New picking <em>%s</em> <b>created</b>.") % (done_picking.name))
            picking.write({'backorder_id': done_picking.id})
            return done_picking
        return self.env['stock.picking']

    @api.cr_uid_ids_context
    def do_transfer(self, cr, uid, picking_ids, context=None):
        """
            If no pack operation, we do simple action_done of the picking
            Otherwise, do the pack operations
        """
        if not context:
            context = {}
        stock_move_obj = self.pool.get('stock.move')
        for picking in self.browse(cr, uid, picking_ids, context=context):
            if not picking.pack_operation_ids:
                self.action_done(cr, uid, [picking.id], context=context)
                continue
            else:
                need_rereserve, all_op_processed = self.picking_recompute_remaining_quantities(cr, uid, picking, context=context)
                #create extra moves in the picking (unexpected product moves coming from pack operations)
                todo_move_ids = []
                if not all_op_processed:
                    todo_move_ids += self._create_extra_moves(cr, uid, picking, context=context)

                #split move lines if needed
                toassign_move_ids = []
                move_lines = [m for m in picking.move_lines if m.state == 'assigned' or m.availability > 0.0]
                for move in move_lines:
                    remaining_qty = move.remaining_qty
                    if move.state in ('done', 'cancel'):
                        #ignore stock moves cancelled or already done
                        continue
                    elif move.state == 'draft':
                        toassign_move_ids.append(move.id)
                    if float_compare(remaining_qty, 0,  precision_rounding = move.product_id.uom_id.rounding) == 0:
                        if move.state in ('draft', 'assigned', 'confirmed'):
                            todo_move_ids.append(move.id)
                    elif float_compare(remaining_qty,0, precision_rounding = move.product_id.uom_id.rounding) > 0 and \
                                float_compare(remaining_qty, move.product_qty, precision_rounding = move.product_id.uom_id.rounding) < 0:
                        new_move = stock_move_obj.split(cr, uid, move, remaining_qty, context=context)
                        todo_move_ids.append(move.id)
                        #Assign move as it was assigned before
                        toassign_move_ids.append(new_move)
                if need_rereserve or not all_op_processed:
                    if not picking.location_id.usage in ("supplier", "production", "inventory"):
                        self.rereserve_quants(cr, uid, picking, move_ids=todo_move_ids, context=context)
                    self.do_recompute_remaining_quantities(cr, uid, [picking.id], context=context)
                if todo_move_ids and not context.get('do_only_split'):
                    self.pool.get('stock.move').action_done(cr, uid, todo_move_ids, context=context)
                elif context.get('do_only_split'):
                    context = dict(context, split=todo_move_ids)
            self._create_backorder(cr, uid, picking, context=context)
            if toassign_move_ids:
                stock_move_obj.action_assign(cr, uid, toassign_move_ids, context=context)
        return True

