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

from openerp import fields, models, api, _
from openerp.tools import float_compare, float_round


class product_putaway_dispatch_strategy(models.Model):
    _inherit = 'product.putaway'

    @api.cr_uid_context
    def _get_putaway_options(self, cr, uid, context=None):
        res = super(product_putaway_dispatch_strategy, self)._get_putaway_options(cr, uid, context)
        res.append(('dispatch', _("Dispatch where needed")))
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
            qty_to_dispatch = {}
            # Get the quantity to dispatch for each product
            for op in transfer.packop_ids:
                # First in packs
                quants = self.env['stock.quant'].browse(op.package_id.get_content())
                if not all([(q.product_id == quants[0].product_id) for q in quants]):
                    # If the pack is not composed of a single product, we prepare unpacking to handle the quants as
                    # bulk products
                    op.prepare_unpack()
                    continue
                for quant in quants:
                    if quant.product_id in qty_to_dispatch:
                        qty_to_dispatch[quant.product_id] += quant.qty
                    else:
                        qty_to_dispatch[quant.product_id] = quant.qty
            for op in transfer.item_ids:
                # Then in bulk products
                if op.product_id in qty_to_dispatch:
                    qty_to_dispatch[op.product_id] += op.quantity
                else:
                    qty_to_dispatch[op.product_id] = op.quantity

            # Iterate on each product
            for product, qty_todo in qty_to_dispatch.iteritems():
                need_moves = self.env['stock.move'].search(
                    [('location_id', 'child_of', transfer.picking_destination_location_id.id),
                     ('product_id', '=', product.id), ('state', '=', 'confirmed')],
                    order="priority DESC, date")
                qty_todo = min(sum([m.product_qty for m in need_moves]), qty_todo)
                location_qty = {}
                qty_left = qty_todo
                # Get the quantity to dispatch for each location and set it in location_qty dict
                for move in need_moves:
                    if float_compare(qty_left, 0, precision_rounding=move.product_uom.rounding) <= 0:
                        break
                    qty_to_add = min(move.product_qty, qty_left)
                    if move.location_id in location_qty:
                        location_qty[move.location_id] += qty_to_add
                    else:
                        location_qty[move.location_id] = qty_to_add
                    qty_left -= qty_to_add

                # First try to dispatch entire packs
                # We only have packs with a single product since we prepared unpacking for the others
                remaining_packops = transfer.packop_ids.filtered(lambda x:
                                                                 self.env['stock.quant'].browse(
                                                                     x.package_id.get_content())[
                                                                     0].product_id == product)
                remaining_packops = remaining_packops.sorted(key=lambda x: sum([q.qty for q in
                                                                                self.env['stock.quant'].browse(
                                                                                    x.package_id.get_content())]),
                                                             reverse=True)
                for op in remaining_packops:
                    # We try to find a location where we need at least the whole qty of the pack
                    for location, qty in location_qty.iteritems():
                        if float_compare(qty, 0, precision_rounding=product.uom_id.rounding) <= 0:
                            continue
                        pack_qty = sum([q.qty for q in self.env['stock.quant'].browse(op.package_id.get_content())])
                        if float_compare(pack_qty, qty, precision_rounding=product.uom_id.rounding) <= 0:
                            # We found a location, so we dispatch the pack to location and go for the next pack
                            op.destinationloc_id = location
                            location_qty[location] -= pack_qty
                            remaining_packops = remaining_packops - op
                            break

                # We prepare unpacking for the remaining packs to handle them as bulk products
                remaining_packops.prepare_unpack()
                # Then we fetch the bulk product operation lines
                op_items = transfer.item_ids.search(
                    [('product_id', '=', product.id), ('transfer_id', '=', transfer.id)])
                # Iterate on each bulk product operations to dispatch them
                for op in op_items:
                    # We get the quantity to dispatch and set the quantity of the operation to 0
                    op_qty_todo = op.quantity
                    op.quantity = 0
                    # We initialize a recordset holding all the lines split from op
                    split_ops = op

                    for location, qty_loc in location_qty.iteritems():
                        if float_compare(op_qty_todo, 0, precision_rounding=product.uom_id.rounding) <= 0:
                            break
                        if float_compare(qty_loc, 0, precision_rounding=product.uom_id.rounding) <= 0:
                            continue
                        qty = min(op_qty_todo, qty_loc)
                        # Check if we have already a line with the wanted destination location
                        for target_op in split_ops:
                            if target_op.destinationloc_id == location:
                                # If we do, we add the quantity to dispatch to this line
                                target_op.quantity += qty
                                break
                        else:
                            # We did not find any line with the wanted location/pack,
                            # so we split the first line to create one
                            new_op = op.copy({
                                'quantity': float_round(qty, precision_rounding=product.uom_id.rounding),
                                'packop_id': False,
                                'destinationloc_id': location.id,
                                'result_package_id': False,
                            })
                            split_ops = split_ops | new_op
                        location_qty[location] -= qty
                        op_qty_todo -= qty
                    # We send back to the source location undispatched moves
                    if float_compare(op_qty_todo, 0, precision_rounding=product.uom_id.rounding) > 0:
                        op.copy({
                            'destinationloc_id': op.sourceloc_id.id,
                            'quantity': float_round(op_qty_todo, precision_rounding=product.uom_id.rounding),
                            'packop_id': False,
                            'result_package_id': False,
                        })
                    # We delete op if it has not been allocated some quantity in between
                    if float_compare(op.quantity, 0, precision_rounding=product.uom_id.rounding) <= 0:
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
            dict_quants_unpacked = {}
            for quant in quants:
                quant_tuple = (quant.package_id,
                               quant.lot_id,
                               quant.owner_id,
                               quant.product_id)
                if dict_quants_unpacked.get(quant_tuple):
                    dict_quants_unpacked[quant_tuple] += quant.qty
                else:
                    dict_quants_unpacked[quant_tuple] = quant.qty
            for key in dict_quants_unpacked.keys():
                self.create({
                    'transfer_id': line.transfer_id.id,
                    'packop_id': False,
                    'quantity': dict_quants_unpacked[key],
                    'product_id': key[3] and key[3].id or False,
                    'product_uom_id': key[3] and key[3].uom_id and key[3].uom_id.id or False,
                    'package_id': key[0] and key[0].id or False,
                    'lot_id': key[1] and key[1].id or False,
                    'sourceloc_id': line.sourceloc_id.id,
                    'destinationloc_id': line.destinationloc_id.id,
                    'result_package_id': key[0] and key[0].id or False,
                    'date': line.date,
                    'owner_id': key[2] and key[2].id or False,
                })
            line.unlink()
