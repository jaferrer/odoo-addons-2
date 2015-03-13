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
            products = []
            # Prepare unpacking of all packs
            transfer.packop_ids.prepare_unpack()
            # Get the products list
            for op in transfer.item_ids:
                if not op.product_id in products:
                    products.append(op.product_id)
            # Get the outgoing moves of all child locations (needs) for each product
            for product_id in products:
                if not product_id in moves:
                    moves[product_id] = self.env['stock.move'].search(
                                                [('location_id','child_of',transfer.picking_destination_location_id.id),
                                                 ('product_id','=',product_id.id),('state','=','confirmed')],
                                                order="priority DESC, date")
            # Iterate on each product
            for product_id, move_list in moves.iteritems():
                op_items = transfer.item_ids.search([('product_id','=',product_id.id),('transfer_id','=',transfer.id)])
                # Iterate on each operation to keep packages, lots and owners intact
                for op in op_items:
                    # We get the quantity to dispatch and set the quantity of the operation to 0
                    qty_todo = op.quantity
                    op.quantity = 0
                    # We initialize a recordset holding all the lines split from op
                    split_ops = op
                    for move in move_list:
                        if qty_todo <= 0:
                            break
                        dest_id = move.location_id
                        qty = min(qty_todo, move.product_qty)
                        # Check if we have already a line with the wanted destination location
                        for target_op in split_ops:
                            if target_op.destinationloc_id == dest_id:
                                # If we do, we add the quantity to dispatch to this line
                                target_op.quantity += qty
                                break
                        else:
                            # We did not find any line with the wanted location/pack,
                            # so we split the first line to create one
                            new_op = op.copy(context=self.env.context)
                            new_op.write({
                                'quantity': qty,
                                'packop_id': False,
                                'destinationloc_id': dest_id.id,
                                'result_package_id': False,
                            })
                            split_ops = split_ops | new_op
                        qty_todo -= qty
                    # We delete op if it has not been allocated some quantity in between
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
