# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from collections import namedtuple

from odoo import models, api, exceptions, _
from odoo.tools.float_utils import float_compare


class StockPickingImproved(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def get_existing_packages(self):
        return self.env['stock.pack.operation'].search([('picking_id', 'in', self.ids)])

    @api.multi
    def do_prepare_partial(self):
        """
        Divide this method into several blocks.
        Cf line 590 odoo -> addons -> stock -> models -> stock_picking.py
        """
        pack_operations = self.env['stock.pack.operation']

        # get list of existing operations and delete them
        existing_packages = self.get_existing_packages()
        if existing_packages:
            existing_packages.unlink()

        for rec in self:
            forced_qties = {}  # Quantity remaining after calculating reserved quants
            picking_quants = self.env['stock.quant']
            # Calculate packages, reserved quants, qtys of this picking's moves
            for move in rec.move_lines:
                more_picking_quants, more_forced_qties = move.compute_move_quantities(forced_qties)
                picking_quants |= more_picking_quants
                forced_qties.update(more_forced_qties)

            pack_ops_vals = rec._prepare_pack_ops(picking_quants, forced_qties)
            for vals in pack_ops_vals:
                vals['fresh_record'] = False
                pack_operations |= self.env['stock.pack.operation'].create(vals)

        # recompute the remaining quantities all at once
        self.do_recompute_remaining_quantities()

        for pack in pack_operations:
            pack.compute_pack_ordered_qty()

        self.write({'recompute_pack_op': False})

    @api.model
    def get_mapping(self):
        return namedtuple('Mapping', ('product', 'package', 'owner', 'location', 'location_dst_id'))

    @api.multi
    def compute_putaway_locations(self, all_products):
        self.ensure_one()
        return dict(
            (product, self.location_dest_id.get_putaway_strategy(product) or self.location_dest_id.id) for product in
            all_products
        )

    @api.model
    def get_product_to_uom(self, all_products):
        return dict((product.id, product.uom_id) for product in all_products)

    @api.multi
    def get_picking_moves(self):
        return self.move_lines.filtered(lambda move: move.state not in ('done', 'cancel'))

    @api.multi
    def get_pack_ops_val_dict(self, mapping, qty, product_to_uom, lots_grouped):
        self.ensure_one()
        uom = product_to_uom[mapping.product.id]
        return {
            'picking_id': self.id,
            'package_id': mapping.package.id,
            'product_qty': mapping.product.uom_id._compute_quantity(qty, uom),
            'location_id': mapping.location.id,
            'location_dest_id': mapping.location_dst_id,
            'owner_id': mapping.owner.id,
            'product_id': mapping.product.id,
            'product_uom_id': uom.id,
            'pack_lot_ids': [
                (0, 0, {
                    'lot_id': lot,
                    'qty': 0.0,
                    'qty_todo': mapping.product.uom_id._compute_quantity(lots_grouped[mapping][lot], uom)
                }) for lot in lots_grouped.get(mapping, {}).keys()],
        }

    @api.multi
    def _prepare_pack_ops(self, quants, forced_qties):
        """
        Divide this method into several blocks.
        Cf line 506 odoo -> addons -> stock -> models -> stock_picking.py
        Prepare pack_operations, returns a list of dict to give at create.
        """
        self.ensure_one()
        valid_quants = quants.get_pack_ops_valid_quants()
        _mapping = self.get_mapping()

        products_from_quants = valid_quants.mapped('product_id')
        products_from_forced_qties = self.env['product.product'].browse(product.id for product in forced_qties.keys())
        products_from_move_lines = self.move_lines.mapped('product_id')
        all_products = products_from_quants | products_from_forced_qties | products_from_move_lines
        computed_putaway_locations = self.compute_putaway_locations(all_products)
        product_to_uom = self.get_product_to_uom(all_products)

        picking_moves = self.get_picking_moves()
        for move in picking_moves:
            move.check_move_uom(product_to_uom)

        picking_moves.check_locations()

        pack_operation_values = []
        # find the packages we can move as a whole, create pack operations and mark related quants as done
        top_lvl_packages = valid_quants._get_top_level_packages(computed_putaway_locations)
        for pack in top_lvl_packages:
            pack_op_vals, pack_quants = pack.top_lvl_package_vals(self, computed_putaway_locations)
            pack_operation_values.append(pack_op_vals)
            valid_quants -= pack_quants

        # Go through all remaining reserved quants and group by product, package, owner, source location and
        # dest location
        # Lots will go into pack operation lot object
        qties_grouped = {}
        lots_grouped = {}
        for quant in valid_quants:
            more_qties_grouped, more_lots_grouped = quant.group_quant(
                _mapping, computed_putaway_locations, qties_grouped, lots_grouped)
            qties_grouped.update(more_qties_grouped)
            lots_grouped.update(more_lots_grouped)

        # Do the same for the forced quantities (in cases of force_assign or incomming shipment for example)
        for product, qty in forced_qties.items():
            if qty <= 0.0:
                continue
            key = _mapping(product,
                           self.env['stock.quant.package'],
                           self.owner_id,
                           self.location_id,
                           computed_putaway_locations[product])
            qties_grouped.setdefault(key, 0.0)
            qties_grouped[key] += qty

        # Create the necessary operations for the grouped quants and remaining qtys
        product_id_to_vals = {}  # use it to create operations using the same order as the picking stock moves
        for mapping, qty in qties_grouped.items():
            val_dict = self.get_pack_ops_val_dict(mapping, qty, product_to_uom, lots_grouped)
            product_id_to_vals.setdefault(mapping.product.id, list()).append(val_dict)

        for move in self.move_lines.filtered(lambda move: move.state not in ('done', 'cancel')):
            values = product_id_to_vals.pop(move.product_id.id, [])
            pack_operation_values += values

        return pack_operation_values


class StockMoveImproved(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def get_assigned_move_forced_qty(self, move_quants):
        self.ensure_one()
        qty = self.product_uom._compute_quantity(self.product_uom_qty, self.product_id.uom_id, round=False)
        forced_qty = qty - sum([x.qty for x in move_quants])
        return forced_qty

    @api.multi
    def update_picking_forced_qties(self, forced_qties, forced_qty):
        """
        if we used force_assign() on the move, or if the move is incoming, forced_qty > 0.
        """
        self.ensure_one()
        updated_forced_qties = dict(forced_qties)
        if updated_forced_qties.get(self.product_id):
            updated_forced_qties[self.product_id] += forced_qty
        else:
            updated_forced_qties[self.product_id] = forced_qty
        return updated_forced_qties

    @api.multi
    def compute_move_quantities(self, forced_qties):
        """
        Calculate packages, reserved quants, qtys of this picking's moves.
        """
        self.ensure_one()
        more_picking_quants = self.env['stock.quant']
        more_forced_qties = dict(forced_qties)
        if self.state not in ('assigned', 'confirmed', 'waiting'):
            return self.env['stock.quant'], {}
        move_quants = self.reserved_quant_ids
        more_picking_quants += move_quants
        forced_qty = 0.0

        if self.state == 'assigned':
            forced_qty = self.get_assigned_move_forced_qty(move_quants)

        # if we used force_assign() on the move, or if the move is incoming, forced_qty > 0
        if float_compare(forced_qty, 0, precision_rounding=self.product_id.uom_id.rounding) > 0:
            more_forced_qties = self.update_picking_forced_qties(forced_qties, forced_qty)

        return more_picking_quants, more_forced_qties

    @api.multi
    def check_move_uom(self, product_to_uom):
        if self.product_uom != product_to_uom[self.product_id.id] and \
                self.product_uom.factor > product_to_uom[self.product_id.id].factor:
            product_to_uom[self.product_id.id] = self.product_uom

    @api.multi
    def check_locations(self):
        if len(self.mapped('location_id')) > 1:
            raise exceptions.UserError(_("The source location must be the same for all the moves of the picking."))
        if len(self.mapped('location_dest_id')) > 1:
            raise exceptions.UserError(_("The destination location must be the same for all the moves of the picking."))


class StockPackOperationImproved(models.Model):
    _inherit = 'stock.pack.operation'

    @api.multi
    def compute_pack_ordered_qty(self):
        self.ensure_one()
        self.ordered_qty = sum(
            self.mapped('linked_move_operation_ids').mapped('move_id').filtered(
                lambda x: x.state != 'cancel').mapped('ordered_qty')
        )

    @api.multi
    def top_lvl_package_vals(self, picking, computed_putaway_locations):
        """
        Find the packages we can move as a whole, create pack operations and mark related quants as done.
        """
        pack_quants = self.get_content()
        pack_op_vals = {
            'picking_id': picking.id,
            'package_id': self.id,
            'product_qty': 1.0,
            'location_id': self.location_id.id,
            'location_dest_id': computed_putaway_locations[pack_quants[0].product_id],
            'owner_id': self.owner_id.id,
        }
        return pack_op_vals, pack_quants


class StockQuantImproved(models.Model):
    _inherit = 'stock.quant'

    @api.multi
    def get_pack_ops_valid_quants(self):
        return self.filtered(lambda x: x.qty > 0)

    @api.multi
    def group_quant(self, _mapping, computed_putaway_locations, qties_grouped, lots_grouped):
        """
        Go through all remaining reserved quants and group by product, package, owner, source location and dest location
        Lots will go into pack operation lot object.
        """
        self.ensure_one()
        more_qties_grouped = dict(qties_grouped)
        more_lots_grouped = dict(lots_grouped)
        key = _mapping(self.product_id,
                       self.package_id,
                       self.owner_id,
                       self.location_id,
                       computed_putaway_locations[self.product_id])

        more_qties_grouped.setdefault(key, 0.0)
        more_qties_grouped[key] += self.qty

        if self.product_id.tracking != 'none' and self.lot_id:
            more_lots_grouped.setdefault(key, dict()).setdefault(self.lot_id.id, 0.0)
            more_lots_grouped[key][self.lot_id.id] += self.qty

        return more_qties_grouped, more_lots_grouped
