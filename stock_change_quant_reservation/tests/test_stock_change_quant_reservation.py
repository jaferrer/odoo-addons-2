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

from openerp import exceptions
from openerp.tests import common


class TestStockChangeQuantReservation(common.TransactionCase):
    def setUp(self):
        super(TestStockChangeQuantReservation, self).setUp()
        self.test_product = self.browse_ref("stock_change_quant_reservation.test_product")
        self.location_suppliers = self.browse_ref("stock.stock_location_suppliers")
        self.location_stock = self.browse_ref("stock.stock_location_stock")
        self.location_shelf = self.browse_ref("stock.stock_location_components")
        self.location_shelf2 = self.browse_ref("stock.stock_location_14")
        self.product_uom_unit_id = self.ref("product.product_uom_unit")
        self.picking_type_id = self.ref("stock.picking_type_internal")

    def test_10_change_moves_chain(self):
        """Test classical workflow"""

        self.assertFalse(self.env['stock.quant'].search([('product_id', '=', self.test_product.id)]))

        move_23_1 = self.env['stock.move'].create({
            'name': "Move 2 => 3 (for quant 1)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 10,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location_shelf2.id,
            'picking_type_id': self.picking_type_id,
        })
        move_23_1.action_confirm()
        move_23_1.action_assign()

        move_23_2 = self.env['stock.move'].create({
            'name': "Move 2 => 3 (for quant 2)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 10,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location_shelf2.id,
            'picking_type_id': self.picking_type_id,
        })
        move_23_2.action_confirm()
        move_23_2.action_assign()

        move_12_1 = self.env['stock.move'].create({
            'name': "Move 1 => 2 (for quant 1)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 10,
            'location_id': self.location_stock.id,
            'location_dest_id': self.location_shelf.id,
            'picking_type_id': self.picking_type_id,
        })
        move_12_1.action_confirm()
        move_12_1.action_assign()

        supply_move_1 = self.env['stock.move'].create({
            'name': "Move supplier => 1 (for quant 1)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 10,
            'location_id': self.location_suppliers.id,
            'location_dest_id': self.location_stock.id,
            'picking_type_id': self.picking_type_id,
        })
        supply_move_1.action_confirm()
        supply_move_1.action_assign()
        supply_move_1.action_done()

        quant_1 = supply_move_1.quant_ids
        self.assertEqual(len(quant_1), 1)
        self.assertEqual(quant_1.qty, 10)
        move_12_1.action_assign()
        self.assertEqual(quant_1.reservation_id, move_12_1)

        move_12_2 = self.env['stock.move'].create({
            'name': "Move 1 => 2 (for quant 2)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 5,
            'location_id': self.location_stock.id,
            'location_dest_id': self.location_shelf.id,
            'picking_type_id': self.picking_type_id,
        })
        move_12_2.action_confirm()
        move_12_2.action_assign()

        supply_move_2 = self.env['stock.move'].create({
            'name': "Move supplier => 1 (for quant 1)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 5,
            'location_id': self.location_suppliers.id,
            'location_dest_id': self.location_stock.id,
            'picking_type_id': self.picking_type_id,
        })
        supply_move_2.action_confirm()
        supply_move_2.action_assign()
        supply_move_2.action_done()
        quant_2 = supply_move_2.quant_ids
        self.assertEqual(len(quant_2), 1)
        self.assertEqual(quant_2.qty, 5)

        move_12_2.action_assign()
        self.assertEqual(move_12_2.reserved_quant_ids, quant_2)

        # Moving quant_1 to shelf

        move_12_1.action_assign()
        self.assertEqual(move_12_1.state, 'assigned')
        self.assertEqual(move_12_1.reserved_quant_ids, quant_1)
        pick_1 = move_12_1.picking_id
        self.assertTrue(pick_1)
        self.assertEqual(pick_1.move_lines, move_12_1)
        pick_1.action_assign()
        pick_1.do_prepare_partial()
        pick_1.do_transfer()
        self.assertEqual(move_12_1.quant_ids, quant_1)
        self.assertEqual(quant_1.location_id, self.location_shelf)
        self.assertEqual(quant_2.location_id, self.location_stock)

        move_23_1.action_assign()
        self.assertEqual(move_23_1.state, 'assigned')
        self.assertEqual(move_23_1.reserved_quant_ids, quant_1)

        # Moving quant_2 to shelf

        move_12_2.action_assign()
        self.assertEqual(move_12_2.state, 'assigned')
        self.assertEqual(move_12_2.reserved_quant_ids, quant_2)
        pick_2 = move_12_2.picking_id
        self.assertTrue(pick_2)
        self.assertEqual(pick_2.move_lines, move_12_2)
        pick_2.action_assign()
        pick_2.do_prepare_partial()
        pick_2.do_transfer()
        self.assertEqual(move_12_2.quant_ids, quant_2)
        self.assertEqual(quant_1.location_id, self.location_shelf)
        self.assertEqual(quant_2.location_id, self.location_shelf)

        move_23_2.action_assign()
        self.assertEqual(move_23_2.state, 'confirmed')
        self.assertEqual(move_23_2.reserved_quant_ids, quant_2)

        # Reassigning quant_1

        assignation_popup = self.env['stock.quant.picking'].with_context(active_ids=quant_1.ids). \
            create({'move_id': move_23_2.id})
        assignation_popup.do_apply()
        self.assertEqual(move_23_1.state, 'confirmed')
        self.assertEqual(move_23_2.state, 'assigned')
        self.assertEqual(move_23_2.reserved_quant_ids, quant_1)
        self.assertFalse(move_12_1.move_dest_id)

    def test_20_change_moves_chain(self):
        """Test that re-assignement of a quant to a new moves change the chains"""

        self.assertFalse(self.env['stock.quant'].search([('product_id', '=', self.test_product.id)]))

        # Creation of the first chain
        move_23_1 = self.env['stock.move'].create({
            'name': "Move 2 => 3 (for quant 1)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 10,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location_shelf2.id,
            'picking_type_id': self.picking_type_id,
        })
        move_23_1.action_confirm()
        move_23_1.action_assign()

        move_12_1 = self.env['stock.move'].create({
            'name': "Move 1 => 2 (for quant 1)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 10,
            'location_id': self.location_stock.id,
            'location_dest_id': self.location_shelf.id,
            'picking_type_id': self.picking_type_id,
            'move_dest_id': move_23_1.id,
        })
        move_12_1.action_confirm()
        move_12_1.action_assign()

        supply_move_1 = self.env['stock.move'].create({
            'name': "Move supplier => 1 (for quant 1)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 10,
            'location_id': self.location_suppliers.id,
            'location_dest_id': self.location_stock.id,
            'picking_type_id': self.picking_type_id,
            'move_dest_id': move_12_1.id,
        })
        supply_move_1.action_confirm()
        supply_move_1.action_assign()
        supply_move_1.action_done()

        quant_1 = supply_move_1.quant_ids
        self.assertEqual(len(quant_1), 1)
        self.assertEqual(quant_1.qty, 10)
        move_12_1.action_assign()
        self.assertEqual(quant_1.reservation_id, move_12_1)

        # Creation of the second chain
        move_23_2 = self.env['stock.move'].create({
            'name': "Move 2 => 3 (for quant 2)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 5,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location_shelf2.id,
            'picking_type_id': self.picking_type_id,
        })
        move_23_2.action_confirm()
        move_23_2.action_assign()

        move_12_2 = self.env['stock.move'].create({
            'name': "Move 1 => 2 (for quant 2)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 5,
            'location_id': self.location_stock.id,
            'location_dest_id': self.location_shelf.id,
            'picking_type_id': self.picking_type_id,
            'move_dest_id': move_23_2.id,
        })
        move_12_2.action_confirm()
        move_12_2.action_assign()

        supply_move_2 = self.env['stock.move'].create({
            'name': "Move supplier => 1 (for quant 1)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 5,
            'location_id': self.location_suppliers.id,
            'location_dest_id': self.location_stock.id,
            'picking_type_id': self.picking_type_id,
            'move_dest_id': move_12_2.id,
        })
        supply_move_2.action_confirm()
        supply_move_2.action_assign()
        supply_move_2.action_done()
        quant_2 = supply_move_2.quant_ids
        self.assertEqual(len(quant_2), 1)
        self.assertEqual(quant_2.qty, 5)

        move_12_2.action_assign()
        self.assertEqual(move_12_2.reserved_quant_ids, quant_2)

        # Moving quant_1 to shelf

        move_12_1.action_assign()
        self.assertEqual(move_12_1.state, 'assigned')
        self.assertEqual(move_12_1.reserved_quant_ids, quant_1)
        pick_1 = move_12_1.picking_id
        self.assertTrue(pick_1)
        self.assertEqual(pick_1.move_lines, move_12_1)
        pick_1.action_assign()
        pick_1.do_prepare_partial()
        pick_1.do_transfer()
        self.assertEqual(move_12_1.quant_ids, quant_1)
        self.assertEqual(quant_1.location_id, self.location_shelf)
        self.assertEqual(quant_2.location_id, self.location_stock)

        # Forcing move_23_2 to steal quant_1 (served for move_23_1)

        self.assertEqual(move_12_1.state, 'done')
        self.assertEqual(move_12_1.quant_ids, quant_1)

        pick_2_1 = move_23_1.picking_id
        self.assertTrue(pick_2_1)
        self.assertEqual(len(pick_2_1.move_lines), 2)
        self.assertIn(move_23_1, pick_2_1.move_lines)
        self.assertIn(move_23_2, pick_2_1.move_lines)
        pick_2_2 = pick_2_1.copy({'move_lines': []})
        move_23_2.picking_id = pick_2_2
        self.assertEqual(pick_2_1.move_lines, move_23_1)
        self.assertEqual(pick_2_2.move_lines, move_23_2)
        pick_2_2.action_assign()
        pick_2_2.do_prepare_partial()
        pick_2_2.do_transfer()
        self.assertEqual(move_23_2.state, 'done')
        self.assertEqual(move_23_2.quant_ids, quant_1)
        self.assertEqual(quant_1.location_id, self.location_shelf2)

        # Move has been stolen. Now, let's action_done move_12_2, assign quant_2 to move_23_1,
        # and check the fixing of the supply chain
        pick_3 = move_12_2.picking_id
        self.assertTrue(pick_3)
        self.assertEqual(pick_3.move_lines, move_12_2)
        # pick_3.action_assign()
        pick_3.do_prepare_partial()
        self.assertEqual(move_12_2.reserved_quant_ids, quant_2)
        pick_3.do_transfer()
        self.assertEqual(move_12_2.state, 'done')
        self.assertEqual(quant_2.location_id, self.location_shelf)
        assignation_popup = self.env['stock.quant.picking'].with_context(active_ids=quant_2.ids). \
            create({'move_id': move_23_1.id})
        assignation_popup.do_apply()
        self.assertEqual(move_23_1.reserved_quant_ids, quant_2)
        self.assertEqual(move_12_2.move_dest_id, move_23_1)

    def test_30_incompatible_qties(self):
        """
        Trying to reserve more quants than move quantity
        """

        self.assertFalse(self.env['stock.quant'].search([('product_id', '=', self.test_product.id)]))

        move_12_1 = self.env['stock.move'].create({
            'name': "Move 1 => 2 (for quant 1)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 10,
            'location_id': self.location_stock.id,
            'location_dest_id': self.location_shelf.id,
            'picking_type_id': self.picking_type_id,
        })
        move_12_1.action_confirm()
        move_12_1.action_assign()

        supply_move_1 = self.env['stock.move'].create({
            'name': "Move supplier => 1 (for quant 1)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 15,
            'location_id': self.location_suppliers.id,
            'location_dest_id': self.location_stock.id,
            'picking_type_id': self.picking_type_id,
        })
        supply_move_1.action_confirm()
        supply_move_1.action_assign()
        supply_move_1.action_done()
        supply_move_1.move_dest_id = move_12_1

        quant_1 = supply_move_1.quant_ids
        self.assertEqual(len(quant_1), 1)
        self.assertEqual(quant_1.qty, 15)

        # Let's check that the system raises an error
        assignation_popup = self.env['stock.quant.picking'].with_context(active_ids=quant_1.ids). \
            create({'move_id': move_12_1.id})
        with self.assertRaises(exceptions.except_orm):
            assignation_popup.do_apply()

    def test_40_move_assign_several_quants(self):
        self.assertFalse(self.env['stock.quant'].search([('product_id', '=', self.test_product.id)]))

        # Creation of the first chain
        move_12_1 = self.env['stock.move'].create({
            'name': "Move 1 => 2 (for quant 1)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 10,
            'location_id': self.location_stock.id,
            'location_dest_id': self.location_shelf.id,
            'picking_type_id': self.picking_type_id,
        })
        move_12_1.action_confirm()
        move_12_1.action_assign()

        supply_move_1 = self.env['stock.move'].create({
            'name': "Move supplier => 1 (for quant 1)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 10,
            'location_id': self.location_suppliers.id,
            'location_dest_id': self.location_stock.id,
            'picking_type_id': self.picking_type_id,
            'move_dest_id': move_12_1.id,
        })
        supply_move_1.action_confirm()
        supply_move_1.action_assign()
        supply_move_1.action_done()

        quant_1 = supply_move_1.quant_ids
        self.assertEqual(len(quant_1), 1)
        self.assertEqual(quant_1.qty, 10)
        move_12_1.action_assign()
        self.assertEqual(quant_1.reservation_id, move_12_1)

        # Creation of the second chain

        move_12_2 = self.env['stock.move'].create({
            'name': "Move 1 => 2 (for quant 2)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 20,
            'location_id': self.location_stock.id,
            'location_dest_id': self.location_shelf.id,
            'picking_type_id': self.picking_type_id,
        })
        move_12_2.action_confirm()
        move_12_2.action_assign()

        supply_move_2 = self.env['stock.move'].create({
            'name': "Move supplier => 1 (for quant 1)",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 5,
            'location_id': self.location_suppliers.id,
            'location_dest_id': self.location_stock.id,
            'picking_type_id': self.picking_type_id,
            'move_dest_id': move_12_2.id,
        })
        supply_move_2.action_confirm()
        supply_move_2.action_assign()
        supply_move_2.action_done()
        quant_2 = supply_move_2.quant_ids
        self.assertEqual(len(quant_2), 1)
        self.assertEqual(quant_2.qty, 5)

        assignation_popup = self.env['stock.quant.picking'].with_context(active_ids=[quant_1.id, quant_2.id]). \
            create({'move_id': move_12_2.id})
        assignation_popup.do_apply()
        self.assertEqual(len(move_12_2.reserved_quant_ids), 2)
        self.assertIn(quant_1, move_12_2.reserved_quant_ids)
        self.assertIn(quant_2, move_12_2.reserved_quant_ids)
