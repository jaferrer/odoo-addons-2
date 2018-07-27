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

from openerp.tests import common


class TestStockPerformanceImproved(common.TransactionCase):

    def setUp(self):
        super(TestStockPerformanceImproved, self).setUp()
        self.product = self.browse_ref("product.product_product_27")
        self.location_stock = self.browse_ref("stock.stock_location_stock")
        self.location_shelf = self.browse_ref("stock.stock_location_components")
        self.location_shelf2 = self.browse_ref("stock.stock_location_14")
        self.location_inv = self.browse_ref("stock.location_inventory")
        self.product_uom_unit_id = self.ref("product.product_uom_unit")
        self.picking_type_id = self.ref("stock.picking_type_internal")
        self.stock = self.browse_ref('stock.stock_location_stock')
        self.package1 = self.browse_ref('stock_performance_improved.package1')
        self.package2 = self.browse_ref('stock_performance_improved.package2')
        self.package3 = self.browse_ref('stock_performance_improved.package3')
        self.product_fix_reserved_moves = self.browse_ref('stock_performance_improved.product')
        self.product_fix_reserved_moves_2 = self.browse_ref('stock_performance_improved.product2')
        self.quant_without_package = self.browse_ref('stock_performance_improved.quant_without_package')
        self.lot1 = self.browse_ref('stock_performance_improved.lot1')
        self.quant1 = self.browse_ref('stock_performance_improved.quant1')
        self.quant2 = self.browse_ref('stock_performance_improved.quant2')
        self.quant3 = self.browse_ref('stock_performance_improved.quant3')
        self.quant4 = self.browse_ref('stock_performance_improved.quant4')
        self.quant5 = self.browse_ref('stock_performance_improved.quant5')
        self.quant6 = self.browse_ref('stock_performance_improved.quant6')
        self.quant7 = self.browse_ref('stock_performance_improved.quant7')
        self.inventory = self.browse_ref('stock_performance_improved.inventory')
        self.inventory2 = self.browse_ref('stock_performance_improved.inventory2')
        self.customer = self.browse_ref('stock.stock_location_customers')
        self.test_product_1 = self.browse_ref('stock_performance_improved.test_product_1')
        self.test_product_2 = self.browse_ref('stock_performance_improved.test_product_2')
        self.move1 = self.browse_ref('stock_performance_improved.move1')
        self.move2 = self.browse_ref('stock_performance_improved.move2')
        self.move3 = self.browse_ref('stock_performance_improved.move3')
        self.unit = self.browse_ref('product.product_uom_unit')
        self.dozen = self.browse_ref('product.product_uom_dozen')
        self.existing_quants = self.env['stock.quant'].search([])
        self.env['stock.location']._parent_store_compute()
        # Call process_prereservations here to test it in all tests
        # self.env['stock.picking'].process_prereservations()

    def test_10_simple_moves(self):
        """Basic checks of picking assignment."""
        move = self.env['stock.move'].create({
            'name': "Test Performance Improved",
            'product_id': self.product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 12,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location_shelf2.id,
            'picking_type_id': self.picking_type_id,
            'defer_picking_assign': True,
        })
        move.action_confirm()
        self.assertFalse(move.picking_id, "Move should not have been assigned to a picking.")

        move2 = self.env['stock.move'].create({
            'name': "Test Performance Improved",
            'product_id': self.product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 10,
            'location_id': self.location_shelf2.id,
            'location_dest_id': self.location_shelf.id,
            'picking_type_id': self.picking_type_id,
            'defer_picking_assign': True,
        })
        move2.action_confirm()
        self.assertFalse(move2.picking_id, "Move should not have been assigned a picking.")

        # Test of assignment with quant in sublocation
        move3 = self.env['stock.move'].create({
            'name': "Test Performance Improved",
            'product_id': self.product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 3,
            'location_id': self.location_stock.id,
            'location_dest_id': self.location_inv.id,
            'picking_type_id': self.picking_type_id,
            'defer_picking_assign': True,
        })
        move3.action_confirm()
        self.assertFalse(move3.picking_id, "Move should not have been assigned a picking.")

        move.action_assign()
        move.action_done()
        move2.action_confirm()
        self.assertFalse(move2.picking_id, "Move should not have been assigned a picking after transfer.")

    def test_15_not_deferred_moves(self):
        """Check that not deferred moves are correctly assigned a picking at confirmation."""
        move2 = self.env['stock.move'].create({
            'name': "Test Performance Improved",
            'product_id': self.product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 10,
            'location_id': self.location_shelf2.id,
            'location_dest_id': self.location_shelf.id,
            'picking_type_id': self.picking_type_id,
        })
        move2.action_confirm()
        self.assertTrue(move2.picking_id, "Move should have been assigned a picking.")

    def test_20_linked_moves(self):
        """Test of linked moves (MTO)."""
        move2 = self.env['stock.move'].create({
            'name': "Test Performance Improved",
            'product_id': self.product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 8,
            'location_id': self.location_shelf2.id,
            'location_dest_id': self.location_shelf.id,
            'picking_type_id': self.picking_type_id,
            'defer_picking_assign': True,
        })
        move = self.env['stock.move'].create({
            'name': "Test Performance Improved",
            'product_id': self.product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 8,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location_shelf2.id,
            'picking_type_id': self.picking_type_id,
            'move_dest_id': move2.id,
            'defer_picking_assign': True,
        })
        move2.action_confirm()
        move.action_confirm()
        self.assertFalse(move.picking_id, "Move should not have been assigned a picking")
        self.assertFalse(move2.picking_id, "Move should not have been assigned a picking")
        move.action_assign()
        move.action_done()
        self.assertFalse(move2.picking_id, "Move should not have been assigned a picking when previous is not done")

    def test_30_check_picking(self):
        """Check if the moves are assigned to the correct picking."""
        move = self.env['stock.move'].create({
            'name': "Test Performance Improved",
            'product_id': self.product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 13,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location_shelf2.id,
            'picking_type_id': self.picking_type_id,
            'defer_picking_assign': False,
        })
        move.action_confirm()
        picking = move.picking_id
        self.assertTrue(picking, "Move should have been assigned a picking.")
        self.assertEqual(picking.state, 'confirmed')
        move2 = self.env['stock.move'].create({
            'name': "Test Performance Improved",
            'product_id': self.product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 9,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location_shelf2.id,
            'picking_type_id': self.picking_type_id,
            'defer_picking_assign': False,
        })
        move2.action_confirm()
        self.assertEqual(move2.picking_id, picking, "Move should have been assigned the existing confirmed picking")
        self.assertEqual(picking.state, 'confirmed')
        picking.action_assign()
        self.assertEqual(picking.state, 'assigned')
        move3 = self.env['stock.move'].create({
            'name': "Test Performance Improved",
            'product_id': self.product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 4,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location_shelf2.id,
            'picking_type_id': self.picking_type_id,
            'defer_picking_assign': False,
        })
        move3.action_confirm()
        self.assertEqual(move3.picking_id, picking, "Move should have been assigned the existing assigned picking")
        picking.do_transfer()
        self.assertEqual(picking.state, 'done')
        for m in [move, move2, move3]:
            self.assertEqual(m.state, 'done')
        move4 = self.env['stock.move'].create({
            'name': "Test Performance Improved",
            'product_id': self.product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 5,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location_shelf2.id,
            'picking_type_id': self.picking_type_id,
            'defer_picking_assign': False,
        })
        move4.action_confirm()
        self.assertTrue(move4.picking_id)
        self.assertNotEqual(move4.picking_id, picking, "Move should have been assigned a new picking")

    def test_40_check_procurements(self):
        """Test that procurements and rules correctly forward defer_picking_assign parameter"""
        location2_id = self.ref('stock_performance_improved.stock_location_b')
        route_id = self.ref('stock_performance_improved.test_route')
        self.product.route_ids = [(6, 0, [route_id])]
        proc = self.env["procurement.order"].create({
            'name': "Test Procurement with deferred picking assign",
            'date_planned': '2015-02-02 00:00:00',
            'product_id': self.product.id,
            'product_qty': 1,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': location2_id,
        })
        proc.run()
        self.assertEqual(proc.state, 'running')
        self.assertGreater(len(proc.move_ids), 0)
        for move in proc.move_ids:
            self.assertEqual(move.defer_picking_assign, True)
            self.assertFalse(move.picking_id)

        rule = self.browse_ref('stock_performance_improved.procurement_rule_a_to_b')
        rule.defer_picking_assign = False
        proc2 = self.env["procurement.order"].create({
            'name': 'Test Procurement without deferred picking assign',
            'date_planned': '2015-02-02 00:00:00',
            'product_id': self.product.id,
            'product_qty': 2,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': location2_id,
        })
        proc2.run()
        self.assertEqual(proc2.state, 'running')
        self.assertGreater(len(proc2.move_ids), 0)
        for move in proc2.move_ids:
            self.assertEqual(move.defer_picking_assign, False)
            self.assertTrue(move.picking_id)

    def test_45_inventory_reserved_moves(self):
        """
        Transferring a reserved quant from a package to another in the same location using stock inventory.
        """
        self.inventory.prepare_inventory()

        move = self.env['stock.move'].create({
            'name': "Test Move",
            'product_id': self.product_fix_reserved_moves.id,
            'product_uom_qty': 10,
            'product_uom': self.product_uom_unit_id,
            'location_id': self.stock.id,
            'location_dest_id': self.customer.id,
        })

        move.action_confirm()
        move.action_assign()
        self.assertEqual(move.state, 'assigned')
        self.assertEqual(move.reserved_quant_ids, self.quant1)
        self.assertEqual(len(self.inventory.line_ids), 3)

        line2 = self.inventory.line_ids.filtered(lambda line: line.product_id == self.product_fix_reserved_moves and
                                                 line.location_id == self.stock and
                                                 line.prod_lot_id == self.lot1 and
                                                 line.package_id == self.package1 and
                                                 line.theoretical_qty == 10.0 and
                                                 line.product_qty == 10.0)
        line3 = self.inventory.line_ids.filtered(lambda line: line.product_id == self.product_fix_reserved_moves and
                                                 line.location_id == self.stock and
                                                 line.prod_lot_id == self.lot1 and
                                                 line.package_id == self.package2 and
                                                 line.theoretical_qty == 20.0 and
                                                 line.product_qty == 20.0)
        self.assertEqual(len(line2), 1)
        self.assertEqual(len(line3), 1)
        line1 = self.inventory.line_ids.filtered(lambda line: line not in [line2, line3])
        self.assertEqual(len(line1), 1)
        self.assertEqual(line1.product_qty, -100)

        line2.product_qty = 0
        line3.product_qty = 30
        self.inventory.action_done()

        self.assertFalse(self.package1.quant_ids)
        self.assertEqual(self.quant_without_package.location_id, self.stock)
        self.assertEqual(self.quant_without_package.qty, -100)
        self.assertFalse(self.quant_without_package.package_id)
        self.assertEqual(self.quant1.location_id, self.location_inv)
        self.assertEqual(self.quant2.location_id, self.stock)
        self.assertEqual(self.quant3.location_id, self.stock)
        self.assertEqual(len(self.package2.quant_ids), 3)
        self.assertIn(self.quant2, self.package2.quant_ids)
        self.assertIn(self.quant3, self.package2.quant_ids)
        self.assertEqual(self.quant2.qty, 5)
        self.assertEqual(self.quant3.qty, 15)
        new_quant = self.package2.quant_ids.filtered(lambda quant: quant not in self.existing_quants)
        self.assertTrue(new_quant)
        self.assertEqual(new_quant.location_id, self.stock)
        self.assertEqual(new_quant.product_id, self.product_fix_reserved_moves)
        self.assertEqual(new_quant.qty, 10)
        self.assertEqual(new_quant.lot_id, self.lot1)

    def test_50_inventory_reserved_moves_bis(self):
        """
        Transferring a reserved quant from a package to another in the same location using stock inventory.
        """
        self.inventory2.prepare_inventory()

        move = self.env['stock.move'].create({
            'name': "Test Move",
            'product_id': self.product_fix_reserved_moves_2.id,
            'product_uom_qty': 20,
            'product_uom': self.product_uom_unit_id,
            'location_id': self.stock.id,
            'location_dest_id': self.customer.id,
        })

        move.action_confirm()
        move.action_assign()
        self.assertEqual(move.state, 'assigned')
        self.assertEqual(move.reserved_quant_ids, self.quant4 | self.quant5 | self.quant6 | self.quant7)
        self.assertEqual(len(self.inventory2.line_ids), 2)

        line1 = self.inventory2.line_ids.filtered(lambda line: line.product_id == self.product_fix_reserved_moves_2 and
                                                  line.location_id == self.stock and
                                                  line.prod_lot_id == self.lot1 and
                                                  line.package_id == self.package3 and
                                                  line.theoretical_qty == 14.0 and
                                                  line.product_qty == 14.0)
        line2 = self.inventory2.line_ids.filtered(lambda line: line.product_id == self.product_fix_reserved_moves_2 and
                                                  line.location_id == self.stock and
                                                  not line.prod_lot_id and
                                                  not line.package_id and
                                                  line.theoretical_qty == 6.0 and
                                                  line.product_qty == 6.0)
        self.assertEqual(len(line1), 1)
        self.assertEqual(len(line2), 1)

        line1.product_qty = 15
        line2.product_qty = 5
        self.inventory2.action_done()

        quants_in_pack3 = self.env['stock.quant'].search([('package_id', '=', self.package3.id)])
        self.assertEqual(sum([q.qty for q in quants_in_pack3]), 15)
        quants_out_of_packs = self.env['stock.quant'].search(
            [('package_id', '=', False), ('product_id', '=', self.product_fix_reserved_moves_2.id),
             ('location_id', '=', self.location_stock.id)]
        )
        self.assertEqual(sum([q.qty for q in quants_out_of_packs]), 5)

    def test_60_packop_units(self):
        self.move1.action_confirm()
        self.move2.action_confirm()
        self.move3.action_confirm()
        picking = self.move1.picking_id
        self.assertTrue(picking)
        self.assertEqual(self.move2.picking_id, picking)
        self.assertEqual(self.move3.picking_id, picking)

        picking.action_assign()
        self.assertEqual(picking.state, 'assigned')

        picking.do_prepare_partial()
        self.assertEqual(len(picking.pack_operation_ids), 3)
        self.assertIn([self.test_product_1, 6.0, self.unit],
                      [[packop.product_id, packop.product_qty, packop.product_uom_id] for
                       packop in picking.pack_operation_ids])
        self.assertIn([self.test_product_1, 2.0, self.dozen],
                      [[packop.product_id, packop.product_qty, packop.product_uom_id] for
                       packop in picking.pack_operation_ids])
        self.assertIn([self.test_product_2, 3.0, self.dozen],
                      [[packop.product_id, packop.product_qty, packop.product_uom_id] for
                       packop in picking.pack_operation_ids])
