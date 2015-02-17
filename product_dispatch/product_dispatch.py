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

from openerp import fields, models, api, _, exceptions

class product_dispatch_strategy(models.Model):
    _inherit = 'product.putaway'

    @api.cr_uid_context
    def _get_putaway_options(self, cr, uid, context=None):
        res = super(product_dispatch_strategy, self)._get_putaway_options(cr, uid, context)
        res.append(('where_needed',_("Where Needed")))
        return res

    method = fields.Selection(_get_putaway_options, "Method", required=True)


class product_dispatch_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'

    @api.multi
    def action_dispatch(self):
        for transfer in self:
            moves = {}
            lines = {}
            managed_packages = []
            for op in transfer.packop_ids:
                # Check for manageable packs (i.e. with only one type of product)
                # Add the quantities inside this pack to the quantity to dispatch
                quants = self.env['stock.quant'].browse(op.package_id.get_content())
                if not quants:
                    continue
                product_id = quants[0].product_id
                if all([(q.product_id == product_id) for q in quants]):
                    managed_packages.append(op.package_id)
                    qty = sum([q.qty for q in quants])
                    if product_id in lines:
                        op.lines[product_id] += qty
                    else:
                        lines[product_id] = qty
            for op in transfer.item_ids:
                # Get quantities for operations
                if op.product_id in lines:
                    lines[op.product_id] += op.quantity
                else:
                    lines[op.product_id] = op.quantity
                op.quantity = 0

            for product_id, qty in lines.iteritems():
                if not product_id in moves:
                    moves[product_id] = self.env['stock.move'].search(
                                                [('location_id','child_of',transfer.picking_destination_location_id.id),
                                                 ('product_id','=',product_id.id),('state','=','confirmed')],
                                                order="priority DESC, date")

            for product_id, move_list in moves.iteritems():
                op_items = transfer.item_ids.search([('product_id','=',product_id.id),('transfer_id','=',transfer.id)])
                op_packs = transfer.packop_ids.search([('package_id','in',[p.id for p in managed_packages]),
                                                       ('transfer_id','=',transfer.id)])
                todo_packs = op_packs.sorted(key=lambda x:sum([q.qty for q in
                                                        self.env['stock.quant'].browse(x.package_id.get_content())]),
                                             reverse=True)
                # if len(op_items) > 1:
                #     raise exceptions.except_orm("Something's gone wrong","There should be only one line per product")
                # op_orig = op_items[0]
                qty_todo = lines[product_id]
                for move in move_list:
                    if qty_todo <= 0:
                        # op_orig.unlink()
                        break
                    dest_id = move.location_id
                    qty = min(qty_todo, move.product_qty)
                    for p in todo_packs:
                        # Check if we can find a pack for this quantity to dispatch
                        pack_qty = sum([q.qty for q in self.env['stock.quant'].browse(p.package_id.get_content())])
                        if pack_qty < qty:
                            p.destinationloc_id = dest_id
                            qty_todo -= pack_qty
                            qty -= pack_qty
                            todo_packs = todo_packs - p

                    for op in op_items:
                        # Dispatch products outside packs
                        if dest_id == op.destinationloc_id:
                            op.quantity += qty
                            qty_todo -= qty
                            break
                    else:
                        new_op = op_items[0].copy(context=self.env.context)
                        new_op.quantity = qty
                        new_op.packop_id = False
                        new_op.destinationloc_id = dest_id
                        qty_todo -= qty
                        op_items = op_items | new_op
                for op in op_items:
                    # Cleaning of empty lines
                    if op.quantity == 0:
                        op.unlink()
        return self.wizard_view()
