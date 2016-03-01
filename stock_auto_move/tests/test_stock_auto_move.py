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


class TestStockAutoMove(common.TransactionCase):
    def setUp(self):
        super(TestStockAutoMove, self).setUp()
        self.product_a1232 = self.browse_ref("product.product_product_6")
        self.location_shelf = self.browse_ref("stock.stock_location_components")
        self.location_1 = self.browse_ref("stock_auto_move.stock_location_a")
        self.location_2 = self.browse_ref("stock_auto_move.stock_location_b")
        self.location_3 = self.browse_ref("stock_auto_move.stock_location_c")
        self.product_uom_unit_id = self.ref("product.product_uom_unit")
        self.picking_type_id = self.ref("stock.picking_type_internal")

    def test_10_auto_move(self):
        """Check automatic processing of move with auto_move set."""
        move = self.env["stock.move"].create({
            'name': "Test Auto",
            'product_id': self.product_a1232.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 12,
            'location_id': self.location_1.id,
            'location_dest_id': self.location_2.id,
            'picking_type_id': self.picking_type_id,
            'auto_move': True,
        })
        move1 = self.env["stock.move"].create({
            'name': "Test Auto 2",
            'product_id': self.product_a1232.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 9,
            'location_id': self.location_1.id,
            'location_dest_id': self.location_2.id,
            'picking_type_id': self.picking_type_id,
            'auto_move': True,
        })
        move2 = self.env["stock.move"].create({
            'name': "Test Manual",
            'product_id': self.product_a1232.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 3,
            'location_id': self.location_1.id,
            'location_dest_id': self.location_2.id,
            'picking_type_id': self.picking_type_id,
            'auto_move': False,
        })
        move.action_confirm()
        self.assertTrue(move.picking_id)
        move1.action_confirm()
        self.assertTrue(move1.picking_id)
        move2.action_confirm()
        self.assertTrue(move2.picking_id)
        self.assertFalse(move2.group_id)
        self.assertEqual(move.state, 'confirmed')
        self.assertEqual(move1.state, 'confirmed')
        self.assertEqual(move2.state, 'confirmed')
        move3 = self.env["stock.move"].create({
            'name': "Supply source location for test",
            'product_id': self.product_a1232.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 25,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location_1.id,
            'auto_move': False,
        })
        move3.action_confirm()
        move3.action_done()
        move.action_assign()
        move1.action_assign()
        move2.action_assign()
        self.assertEqual(move3.state, 'done')
        self.assertEqual(move2.state, 'assigned')
        self.assertEqual(move.state, 'done')
        self.assertEqual(move1.state, 'done')

        self.assertTrue(move1.picking_id)
        self.assertTrue(move2.picking_id)
        self.assertNotEqual(move1.picking_id, move2.picking_id)

    def test_20_procurement_auto_move(self):
        """Check that move generated with procurement rule have auto_move set."""
        self.product_a1232.route_ids = [(4, self.ref("stock_auto_move.test_route"))]
        proc = self.env["procurement.order"].create({
            'name': 'Test Procurement with auto_move',
            'date_planned': '2015-02-02 00:00:00',
            'product_id': self.product_a1232.id,
            'product_qty': 1,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_2.id,
        })
        proc.check()
        proc.run()
        self.assertEqual(proc.rule_id.id, self.ref("stock_auto_move.procurement_rule_a_to_b"))

        for move in proc.move_ids:
            self.assertEqual(move.auto_move, True)
            self.assertEqual(move.state, 'confirmed')

    def test_30_push_rule_auto(self):
        """Checks that push rule with auto set leads to an auto_move."""
        self.product_a1232.route_ids = [(4, self.ref("stock_auto_move.test_route"))]
        move3 = self.env["stock.move"].create({
            'name': "Supply source location for test",
            'product_id': self.product_a1232.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 7,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location_3.id,
            'auto_move': False,
        })
        move3.action_confirm()
        move3.action_done()
        quants_in_3 = self.env['stock.quant'].search([('product_id', '=', self.product_a1232.id),
                                                      ('location_id', '=', self.location_3.id)])
        quants_in_1 = self.env['stock.quant'].search([('product_id', '=', self.product_a1232.id),
                                                      ('location_id', '=', self.location_1.id)])
        self.assertEqual(len(quants_in_3), 0)
        self.assertGreater(len(quants_in_1), 0)

    def test_40_picking_split(self):
        """
        Testing the picking split for auto_moves in same picking which are children of moves from different pickings
        """
        self.env['stock.quant'].create({
            'product_id': self.product_a1232.id,
            'qty': 15,
            'location_id': self.location_1.id,
        })
        picking1 = self.env['stock.picking'].create({
            'name': "Picking 1",
            'picking_type_id': self.picking_type_id,
        })
        picking2 = self.env['stock.picking'].create({
            'name': "Picking 2",
            'picking_type_id': self.picking_type_id,
        })
        picking3 = self.env['stock.picking'].create({
            'name': "Picking 3",
            'picking_type_id': self.picking_type_id,
        })
        move2 = self.env["stock.move"].create({
            'name': "Move 2",
            'product_id': self.product_a1232.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 5,
            'location_id': self.location_2.id,
            'location_dest_id': self.location_3.id,
            'picking_type_id': self.picking_type_id,
            'auto_move': True,
            'picking_id': picking3.id
        })
        move1 = self.env["stock.move"].create({
            'name': "Move 1",
            'product_id': self.product_a1232.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 5,
            'location_id': self.location_1.id,
            'location_dest_id': self.location_2.id,
            'picking_type_id': self.picking_type_id,
            'auto_move': False,
            'move_dest_id': move2.id,
            'picking_id': picking1.id
        })
        move4 = self.env["stock.move"].create({
            'name': "Move 4",
            'product_id': self.product_a1232.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 10,
            'location_id': self.location_2.id,
            'location_dest_id': self.location_3.id,
            'picking_type_id': self.picking_type_id,
            'auto_move': True,
            'picking_id': picking3.id
        })
        move3 = self.env["stock.move"].create({
            'name': "Move 3",
            'product_id': self.product_a1232.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 10,
            'location_id': self.location_1.id,
            'location_dest_id': self.location_2.id,
            'picking_type_id': self.picking_type_id,
            'auto_move': False,
            'move_dest_id': move4.id,
            'picking_id': picking2.id
        })

        move1.action_confirm()
        move2.action_confirm()
        move3.action_confirm()
        move4.action_confirm()

        picking1.do_transfer()
        self.assertEqual(move1.state, 'done')
        self.assertEqual(move2.state, 'done')
        self.assertEqual(move1.picking_id, picking1)
        self.assertEqual(move3.picking_id, picking2)
        self.assertEqual(move4.picking_id, picking3)
        self.assertTrue(move2.picking_id)
        self.assertNotIn(move2.picking_id, [picking1, picking2, picking3])
        self.assertEqual(move3.state, 'confirmed')
        self.assertEqual(move4.state, 'waiting')
