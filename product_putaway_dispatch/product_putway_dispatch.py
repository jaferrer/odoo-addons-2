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

class product_putaway_dispatch_strategy(models.Model):
    _inherit = 'product.putaway'

    @api.cr_uid_context
    def _get_putaway_options(self, cr, uid, context=None):
        res = super(product_putaway_dispatch_strategy, self)._get_putaway_options(cr, uid, context)
        res.append(('dispatch',_("Dispatch where needed")))
        return res

    method = fields.Selection(_get_putaway_options, "Method", required=True)


class product_putaway_dispatch_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'

    hide_dispatch_button = fields.Boolean("Hide Dispatch Button", compute="_compute_hide_dispatch_button")

    @api.depends('picking_destination_location_id.putaway_strategy_id')
    def _compute_hide_dispatch_button(self):
        for rec in self:
            rec.hide_dispatch_button = (rec.picking_destination_location_id.putaway_strategy_id.method != 'dispatch')

    @api.multi
    def action_dispatch(self):
        for transfer in self:
            moves = {}
            lines = {}
            managed_packages = []
            # Prepare unpacking of all packs
            transfer.packop_ids.prepare_unpack()
            # Get quantities for operations
            for op in transfer.item_ids:
                if op.product_id in lines:
                    lines[op.product_id] += op.quantity
                else:
                    lines[op.product_id] = op.quantity
                op.quantity = 0
            # Get the outgoing moves of all child locations (needs) for each product
            for product_id, qty in lines.iteritems():
                if not product_id in moves:
                    moves[product_id] = self.env['stock.move'].search(
                                                [('location_id','child_of',transfer.picking_destination_location_id.id),
                                                 ('product_id','=',product_id.id),('state','=','confirmed')],
                                                order="priority DESC, date")

            for product_id, move_list in moves.iteritems():
                op_items = transfer.item_ids.search([('product_id','=',product_id.id),('transfer_id','=',transfer.id)])
                # op_packs = transfer.packop_ids.search([('package_id','in',[p.id for p in managed_packages]),
                #                                        ('transfer_id','=',transfer.id)])
                # todo_packs = op_packs.sorted(key=lambda x:sum([q.qty for q in
                #                                         self.env['stock.quant'].browse(x.package_id.get_content())]),
                #                              reverse=True)
                qty_todo = lines[product_id]
                for move in move_list:
                    if qty_todo <= 0:
                        break
                    dest_id = move.location_id
                    qty = min(qty_todo, move.product_qty)
                    for op in op_items:
                        # Check if we already have a transfer line to the wanted location (dest_id)
                        if op.destinationloc_id == dest_id:
                            # If we do, we add the quantity to dispatch to this line
                            op.quantity += qty
                            qty_todo -= qty
                            break
                    else:
                        # We did not find any line with the wanted location, so we split the first line to create one
                        new_op = op_items[0].copy(context=self.env.context)
                        new_op.write({
                            'quantity': qty,
                            'packop_id': False,
                            'destinationloc_id': dest_id.id,
                            'result_package_id': False,
                        })
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


class product_putaway_dispatch_transfer_details_items(models.TransientModel):
    _inherit = 'stock.transfer_details_items'

    @api.multi
    def prepare_unpack(self):
        """Moves the line from the package to move list to the product to move list.
        This is done with keeping source package and destination package to the items current pack."""
        for line in self:
            quants = self.env['stock.quant'].browse(line.package_id.get_content())
            for quant in quants:
                new_id = self.create({
                    'transfer_id': line.transfer_id.id,
                    'packop_id': False,
                    'quantity': quant.qty,
                    'product_id': quant.product_id.id,
                    'product_uom_id': quant.product_id.uom_id.id,
                    'package_id': quant.package_id.id,
                    'lot_id': quant.lot_id.id,
                    'sourceloc_id': line.sourceloc_id.id,
                    'destinationloc_id': line.destinationloc_id.id,
                    'result_package_id': quant.package_id.id,
                    'date': line.date,
                    'owner_id': quant.owner_id.id,
                })
            line.unlink()
