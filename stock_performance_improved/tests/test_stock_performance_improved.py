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
        self.assertTrue(move.picking_id, "Move should have been assigned a picking.")

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
        self.assertTrue(move3.picking_id, "Move should have been assigned a picking.")

        move.action_assign()
        move.action_done()
        move2.action_confirm()
        self.assertTrue(move2.picking_id, "Move should have been assigned a picking after transfer.")

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
        """Test of linked moves."""
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
        self.assertTrue(move.picking_id, "Move should have been assigned a picking")
        self.assertFalse(move2.picking_id, "Move should not have been assigned a picking")
        move.action_assign()
        move.action_done()
        self.assertTrue(move2.picking_id, "Move should have been assigned a picking when previous is done")

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
            'defer_picking_assign': True,
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
            'defer_picking_assign': True,
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
            'defer_picking_assign': True,
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
            'defer_picking_assign': True,
        })
        move4.action_confirm()
        self.assertTrue(move4.picking_id)
        self.assertNotEqual(move4.picking_id, picking, "Move should have been assigned a new picking")

    def test_40_check_procurements(self):
        """Test that procurements and rules correctly forward defer_picking_assign parameter"""
        location1_id = self.ref('stock_performance_improved.stock_location_a')
        location2_id = self.ref('stock_performance_improved.stock_location_b')
        route_id = self.ref('stock_performance_improved.test_route')
        self.product.route_ids = [(6, 0, [route_id])]
        proc = self.env["procurement.order"].create({
            'name': 'Test Procurement with deferred picking assign',
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
