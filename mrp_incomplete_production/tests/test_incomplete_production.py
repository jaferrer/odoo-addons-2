# -*- coding: utf8 -*-
#
# Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from datetime import *
from openerp.tests import common
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class TestIncompleteProduction(common.TransactionCase):
    def setUp(self):
        super(TestIncompleteProduction, self).setUp()
        self.company = self.browse_ref('base.main_company')
        self.product_to_manufacture1 = self.browse_ref('mrp_incomplete_production.product_to_manufacture1')
        self.unit = self.browse_ref('product.product_uom_unit')
        self.location1 = self.browse_ref('stock.stock_location_stock')
        self.location2 = self.browse_ref('stock.location_dispatch_zone')
        self.location3 = self.browse_ref('stock.location_order')
        self.location4 = self.browse_ref('stock.location_inventory')
        self.return_location = self.browse_ref('mrp_incomplete_production.return_location')
        self.stock_picking_type_return = self.browse_ref('mrp_incomplete_production.stock_picking_type_return')
        self.product1 = self.browse_ref('mrp_incomplete_production.product1')
        self.product2 = self.browse_ref('mrp_incomplete_production.product2')
        self.product3 = self.browse_ref('mrp_incomplete_production.product3')
        self.bom1 = self.browse_ref('mrp_incomplete_production.bom1')
        self.line1 = self.browse_ref('mrp_incomplete_production.line1')
        self.line2 = self.browse_ref('mrp_incomplete_production.line2')
        self.line3 = self.browse_ref('mrp_incomplete_production.line3')
        self.rule1 = self.browse_ref('mrp_incomplete_production.rule1')
        self.procurement1 = self.browse_ref('mrp_incomplete_production.procurement1')
        self.warehouse1 = self.browse_ref('stock.warehouse0')

    def production_check(self, product_qty=1):
        mrp_production1 = self.env['mrp.production'].create({
            'name': 'mrp_production1',
            'product_id': self.product_to_manufacture1.id,
            'product_qty': product_qty,
            'product_uom': self.unit.id,
            'location_src_id': self.location1.id,
            'location_dest_id': self.location1.id,
            'date_planned': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'bom_id': self.bom1.id,
            'company_id': self.company.id,
        })
        self.assertTrue(mrp_production1)
        mrp_production1.signal_workflow('button_confirm')
        self.assertEquals(len(mrp_production1.move_lines), 3)
        [move1, move2, move3] = [False] * 3
        for move in mrp_production1.move_lines:
            move.action_assign()
            if move.product_qty == 5 * product_qty and move.product_id == self.product1:
                move1 = move
            if move.product_qty == 10 * product_qty and move.product_id == self.product2:
                move2 = move
            if move.product_qty == 15 * product_qty and move.product_id == self.product3:
                move3 = move
        self.assertTrue(move1)
        self.assertTrue(move2)
        self.assertTrue(move3)
        return mrp_production1, move1, move2, move3

    def bring_quant_for_move(self, move):
        incoming_move = self.env['stock.move'].create({
            'name': "Incoming move for product 2",
            'product_id': move.product_id.id,
            'product_uom_qty': move.product_uom_qty,
            'product_uom': move.product_uom.id,
            'location_id': self.location4.id,
            'location_dest_id': move.location_id.id,
            'move_dest_id': move.id,
        })
        incoming_move.action_confirm()
        incoming_move.action_assign()
        self.assertEqual(incoming_move.state, 'assigned')
        incoming_move.action_done()
        self.assertEqual(len(incoming_move.quant_ids), 1)
        self.assertEqual(incoming_move.quant_ids.qty, move.product_uom_qty)
        move.action_assign()
        self.assertEqual(move.state, 'assigned')
        self.assertEqual(move.reserved_quant_ids, incoming_move.quant_ids)

    def test_10_incomplete_production(self):
        """Test with one move available: move1"""
        mrp_production1, move1, move2, move3 = self.production_check()
        self.bring_quant_for_move(move1)
        self.assertEquals(move1.state, 'assigned')
        self.assertEquals(move2.state, 'confirmed')
        self.assertEquals(move3.state, 'confirmed')
        mrp_production1.action_assign()
        self.assertEqual(mrp_production1.state, 'ready')
        mrp_product_produce1_data = {
            'production_id': mrp_production1.id,
            'consume_lines': [(0, 0, vals) for vals in mrp_production1._calculate_qty(mrp_production1)]
        }
        mrp_product_produce1 = self.env['mrp.product.produce'].with_context({'active_id': mrp_production1.id}). \
            create(mrp_product_produce1_data)
        self.assertEqual(len(mrp_product_produce1.consume_lines), 1)
        self.assertEqual(mrp_product_produce1.consume_lines[0].product_id, self.product1)
        self.assertEqual(mrp_product_produce1.consume_lines[0].product_qty, self.line1.product_qty)
        self.assertEqual(mrp_product_produce1.child_src_loc_id, mrp_production1.location_src_id)
        self.assertEqual(mrp_product_produce1.child_dest_loc_id, mrp_production1.location_dest_id)
        self.assertEqual(mrp_product_produce1.child_production_product_id, mrp_production1.product_id)

        self.assertEquals(move1.state, 'assigned')
        self.assertEquals(move2.state, 'confirmed')
        self.assertEquals(move3.state, 'confirmed')
        mrp_product_produce1.do_produce()

        self.assertEqual(mrp_production1.state, 'done')
        self.assertFalse(mrp_production1.move_lines)
        self.assertEqual(len(mrp_production1.move_lines2), 3)
        list_move_lines2 = [(x.product_id, x.product_qty, x.product_uom, x.state) for x in mrp_production1.move_lines2]
        self.assertIn((self.product1, 5, move1.product_uom, 'done'), list_move_lines2)
        self.assertIn((self.product2, 10, move2.product_uom, 'cancel'), list_move_lines2)
        self.assertIn((self.product3, 15, move3.product_uom, 'cancel'), list_move_lines2)
        self.assertTrue(mrp_production1.child_move_ids)
        self.assertEqual(len(mrp_production1.child_move_ids), 2)
        list_not_consumed = [(x.product_id, x.product_qty, x.product_uom) for x in mrp_production1.child_move_ids]
        self.assertIn((self.product2, 10, move2.product_uom), list_not_consumed)
        self.assertIn((self.product3, 15, move3.product_uom), list_not_consumed)
        self.assertTrue(mrp_production1.child_order_id)

        mrp_production2 = mrp_production1.child_order_id
        self.assertFalse(mrp_production2.move_lines2)
        self.assertFalse(mrp_production2.child_move_ids)
        self.assertEqual(len(mrp_production2.move_lines), 2)
        list_move_lines = [(x.product_id, x.product_qty, x.product_uom, x.state) for x in mrp_production2.move_lines]
        self.assertIn((self.product2, 10, move2.product_uom, 'confirmed'), list_move_lines)
        self.assertIn((self.product3, 15, move3.product_uom, 'confirmed'), list_move_lines)
        self.assertTrue(mrp_production2.backorder_id)
        self.assertEqual(mrp_production2.backorder_id, mrp_production1)
        self.assertFalse(mrp_production2.child_order_id)

    def test_20_incomplete_production(self):
        """Test with two moves available and specific parameters for product.produce object."""
        mrp_production1, move1, move2, move3 = self.production_check()
        self.bring_quant_for_move(move1)
        self.bring_quant_for_move(move2)
        mrp_production1.action_assign()
        self.assertEqual(mrp_production1.state, 'ready')
        mrp_product_produce1_data = {
            'production_id': mrp_production1.id,
            'consume_lines': [(0, 0, vals) for vals in mrp_production1._calculate_qty(mrp_production1)]
        }
        mrp_product_produce1 = self.env['mrp.product.produce'].with_context({'active_id': mrp_production1.id}). \
            create(mrp_product_produce1_data)
        self.assertEqual(len(mrp_product_produce1.consume_lines), 2)
        liste_consume = [(x.product_id, x.product_qty) for x in mrp_product_produce1.consume_lines]
        self.assertIn((self.product1, 5), liste_consume)
        self.assertIn((self.product2, 10), liste_consume)
        mrp_product_produce1.child_src_loc_id = self.location1
        mrp_product_produce1.child_dest_loc_id = self.location2
        mrp_product_produce1.child_production_product_id = self.product1

        mrp_product_produce1.do_produce()

        self.assertTrue(mrp_production1.child_order_id)
        mrp_production2 = mrp_production1.child_order_id
        self.assertEqual(mrp_production2.product_id, self.product1)
        self.assertEqual(mrp_production2.location_src_id, self.location1)
        self.assertEqual(mrp_production2.location_dest_id, self.location2)
        list_consume_lines = [(x.product_id, x.product_qty) for x in mrp_product_produce1.consume_lines]
        self.assertEqual(len(list_consume_lines), 2)
        self.assertIn((self.product1, 5), list_consume_lines)
        self.assertIn((self.product2, 10), list_consume_lines)

        self.assertFalse(mrp_production1.move_lines)
        self.assertEqual(len(mrp_production1.move_lines2), 3)
        list_move_lines2 = [(x.product_id, x.product_qty, x.product_uom, x.state) for x in mrp_production1.move_lines2]
        self.assertIn((self.product1, 5, move1.product_uom, 'done'), list_move_lines2)
        self.assertIn((self.product2, 10, move2.product_uom, 'done'), list_move_lines2)
        self.assertIn((self.product3, 15, move3.product_uom, 'cancel'), list_move_lines2)
        self.assertEqual(len(mrp_production1.child_move_ids), 1)
        self.assertEqual(mrp_production1.child_move_ids[0].product_id, self.product3)
        self.assertEqual(mrp_production1.child_move_ids[0].product_qty, 15)

        self.assertFalse(mrp_production2.move_lines2)
        self.assertFalse(mrp_production2.child_move_ids)
        self.assertEqual(len(mrp_production2.move_lines), 1)
        x = mrp_production2.move_lines[0]
        list_move_lines = (x.product_id, x.product_qty, x.product_uom, x.state)
        self.assertEqual((self.product3, 15, move3.product_uom, 'confirmed'), list_move_lines)

    def test_30_incomplete_production(self):
        """Test of cascade."""
        mrp_production1, move1, move2, move3 = self.production_check()
        self.bring_quant_for_move(move1)
        mrp_production1.action_ready()
        self.assertEqual(mrp_production1.state, 'ready')
        mrp_product_produce1_data = {
            'production_id': mrp_production1.id,
            'consume_lines': [(0, 0, vals) for vals in mrp_production1._calculate_qty(mrp_production1)]
        }
        mrp_product_produce1 = self.env['mrp.product.produce'].with_context({'active_id': mrp_production1.id}). \
            create(mrp_product_produce1_data)
        mrp_product_produce1.do_produce()
        self.assertEqual(mrp_production1.state, 'done')
        self.assertEqual(len(mrp_production1.child_move_ids), 2)
        self.assertTrue(mrp_production1.child_order_id)
        mrp_production2 = mrp_production1.child_order_id

        list_move = [x for x in mrp_production2.move_lines if x.product_id == self.product2]
        self.assertEqual(len(list_move), 1)
        move = list_move[0]
        self.bring_quant_for_move(move)
        mrp_production2.action_ready()
        self.assertEqual(mrp_production2.state, 'ready')
        mrp_product_produce2_data = {
            'production_id': mrp_production2.id,
            'consume_lines': [(0, 0, vals) for vals in mrp_production2._calculate_qty(mrp_production2)]
        }
        mrp_product_produce2 = self.env['mrp.product.produce'].with_context({'active_id': mrp_production2.id}). \
            create(mrp_product_produce2_data)
        mrp_product_produce2.do_produce()
        self.assertEqual(mrp_production2.state, 'done')
        self.assertEqual(len(mrp_production2.child_move_ids), 1)
        self.assertTrue(mrp_production2.child_order_id)
        mrp_production3 = mrp_production2.child_order_id

        self.assertEqual(len(mrp_production3.move_lines), 1)
        move = mrp_production3.move_lines[0]
        self.assertEqual(move.product_id, self.product3)
        self.bring_quant_for_move(move)
        mrp_production3.action_ready()
        self.assertEqual(mrp_production3.state, 'ready')
        mrp_product_produce3_data = {
            'production_id': mrp_production3.id,
            'consume_lines': [(0, 0, vals) for vals in mrp_production3._calculate_qty(mrp_production3)]
        }
        mrp_product_produce3 = self.env['mrp.product.produce'].with_context({'active_id': mrp_production3.id}). \
            create(mrp_product_produce3_data)
        mrp_product_produce3.do_produce()
        self.assertFalse(mrp_production3.child_order_id)
        self.assertFalse(mrp_production3.child_move_ids)
        self.assertEqual(mrp_production3.state, 'done')

    def test_40_incomplete_production(self):
        """test automatic generation of a MO."""
        procurement = self.procurement1
        procurement.run()
        self.assertTrue(procurement.production_id)
        mrp_production1 = procurement.production_id
        self.assertEqual(mrp_production1.child_location_id, self.location1)

    def test_50_incomplete_production(self):
        """Test of BOM update."""
        mrp_production1, move1, move2, move3 = self.production_check()
        self.bring_quant_for_move(move1)
        mrp_production1.action_ready()
        self.assertEqual(mrp_production1.state, 'ready')
        mrp_product_produce1_data = {
            'production_id': mrp_production1.id,
            'consume_lines': [(0, 0, vals) for vals in mrp_production1._calculate_qty(mrp_production1)]
        }
        mrp_product_produce1 = self.env['mrp.product.produce'].with_context({'active_id': mrp_production1.id}). \
            create(mrp_product_produce1_data)
        mrp_product_produce1.do_produce()
        self.assertTrue(mrp_production1.child_order_id)
        mrp_production2 = mrp_production1.child_order_id
        self.assertEqual(mrp_production2.product_id, self.product_to_manufacture1)
        mrp_production2.button_update()
        self.assertEqual(len(mrp_production2.move_lines), 2)

    def test_60_incomplete_production(self):
        """Returning raw materials provided by several quants."""

        def create_service_move(move, qty):
            new_move = self.env['stock.move'].create({
                'name': "Service move for move %s" % move.name,
                'product_id': move.product_id.id,
                'product_uom_qty': qty,
                'product_uom': self.unit.id,
                'move_dest_id': move.id,
                'location_id': self.browse_ref('stock.stock_location_suppliers').id,
                'location_dest_id': move.location_id.id,
            })
            new_move.action_assign()
            new_move.action_done()

        mrp_production1, move1, move2, move3 = self.production_check()
        self.assertFalse(self.env['stock.quant'].search([('product_id', '=', self.product_to_manufacture1.id)]))
        self.assertFalse(self.env['stock.quant'].search([('product_id', '=', self.product1.id)]))
        self.assertFalse(self.env['stock.quant'].search([('product_id', '=', self.product2.id)]))
        self.assertFalse(self.env['stock.quant'].search([('product_id', '=', self.product3.id)]))
        # Creation of service moves
        create_service_move(move1, 2)
        create_service_move(move1, 3)

        create_service_move(move2, 1)
        create_service_move(move2, 3)
        create_service_move(move2, 2)
        create_service_move(move2, 4)

        create_service_move(move3, 5)
        create_service_move(move3, 3)
        create_service_move(move3, 7)

        mrp_production1.action_assign()
        self.assertEqual(mrp_production1.state, 'ready')
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(move2.state, 'assigned')
        self.assertEqual(move3.state, 'assigned')

        mrp_product_produce1_data = {
            'production_id': mrp_production1.id,
            'consume_lines': [(0, 0, vals) for vals in mrp_production1._calculate_qty(mrp_production1)]
        }
        mrp_product_produce1 = self.env['mrp.product.produce'].with_context({'active_id': mrp_production1.id}). \
            create(mrp_product_produce1_data)

        self.assertTrue(mrp_product_produce1.create_child)
        self.assertTrue(mrp_product_produce1.return_raw_materials)
        mrp_product_produce1.return_location_id = self.return_location.id
        self.assertEqual(len(mrp_product_produce1.consume_lines), 3)
        self.assertIn(self.product1, [cl.product_id for cl in mrp_product_produce1.consume_lines])
        self.assertIn(self.product2, [cl.product_id for cl in mrp_product_produce1.consume_lines])
        self.assertIn(self.product3, [cl.product_id for cl in mrp_product_produce1.consume_lines])
        for line in mrp_product_produce1.consume_lines:
            if line.product_id == self.product1:
                self.assertEqual(line.product_qty, 5)
                line.product_qty = 1
            elif line.product_id == self.product2:
                self.assertEqual(line.product_qty, 10)
                line.product_qty = 1.5
            elif line.product_id == self.product3:
                self.assertEqual(line.product_qty, 15)
                line.product_qty = 11

        mrp_product_produce1.with_context(force_return_picking_type=self.stock_picking_type_return).do_produce()

        # Checking child order data
        self.assertTrue(mrp_production1.child_order_id)
        self.assertEqual(len(mrp_production1.child_order_id.move_lines), 3)
        self.assertIn((self.product1, 4),
                      [(move.product_id, move.product_uom_qty) for move in mrp_production1.child_order_id.move_lines])
        self.assertIn((self.product2, 8.5),
                      [(move.product_id, move.product_uom_qty) for move in mrp_production1.child_order_id.move_lines])
        self.assertIn((self.product3, 4),
                      [(move.product_id, move.product_uom_qty) for move in mrp_production1.child_order_id.move_lines])

        # Checking return picking data
        picking = self.env['stock.picking'].search([('picking_type_id', '=', self.stock_picking_type_return.id)])
        self.assertEqual(len(picking.move_lines), 3)
        self.assertIn((self.product1, 4), [(move.product_id, move.product_uom_qty) for move in picking.move_lines])
        self.assertIn((self.product2, 8.5), [(move.product_id, move.product_uom_qty) for move in picking.move_lines])
        self.assertIn((self.product3, 4), [(move.product_id, move.product_uom_qty) for move in picking.move_lines])

    def test_70_incomplete_production(self):
        """Same test as previous one, but one move is partially available (and ont is not available at all)."""

        def create_service_move(move, qty):
            new_move = self.env['stock.move'].create({
                'name': "Service move for move %s" % move.name,
                'product_id': move.product_id.id,
                'product_uom_qty': qty,
                'product_uom': self.unit.id,
                'move_dest_id': move.id,
                'location_id': self.browse_ref('stock.stock_location_suppliers').id,
                'location_dest_id': move.location_id.id,
            })
            new_move.action_assign()
            new_move.action_done()

        mrp_production1, move1, move2, move3 = self.production_check()
        self.assertFalse(self.env['stock.quant'].search([('product_id', '=', self.product_to_manufacture1.id)]))
        self.assertFalse(self.env['stock.quant'].search([('product_id', '=', self.product1.id)]))
        self.assertFalse(self.env['stock.quant'].search([('product_id', '=', self.product2.id)]))
        self.assertFalse(self.env['stock.quant'].search([('product_id', '=', self.product3.id)]))
        # Creation of service moves
        create_service_move(move1, 5)
        create_service_move(move3, 10)

        mrp_production1.action_assign()
        self.assertEqual(mrp_production1.state, 'ready')
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(move2.state, 'confirmed')
        self.assertFalse(move2.reserved_quant_ids)
        self.assertEqual(move3.state, 'confirmed')
        self.assertEqual(len(move3.reserved_quant_ids), 1)
        self.assertEqual(move3.reserved_quant_ids.qty, 10)

        mrp_product_produce1_data = {
            'production_id': mrp_production1.id,
            'consume_lines': [(0, 0, vals) for vals in mrp_production1._calculate_qty(mrp_production1)]
        }
        mrp_product_produce1 = self.env['mrp.product.produce'].with_context({'active_id': mrp_production1.id}). \
            create(mrp_product_produce1_data)

        self.assertTrue(mrp_product_produce1.create_child)
        self.assertTrue(mrp_product_produce1.return_raw_materials)
        mrp_product_produce1.return_location_id = self.return_location.id
        self.assertEqual(len(mrp_product_produce1.consume_lines), 2)
        self.assertEqual(mrp_product_produce1.product_qty, 1)
        self.assertIn(self.product1, [cl.product_id for cl in mrp_product_produce1.consume_lines])
        self.assertNotIn(self.product2, [cl.product_id for cl in mrp_product_produce1.consume_lines])
        self.assertIn(self.product3, [cl.product_id for cl in mrp_product_produce1.consume_lines])
        for line in mrp_product_produce1.consume_lines:
            if line.product_id == self.product1:
                self.assertEqual(line.product_qty, 5)
                line.product_qty = 1
            elif line.product_id == self.product3:
                self.assertEqual(line.product_qty, 10)
                line.product_qty = 8

        mrp_product_produce1.with_context(force_return_picking_type=self.stock_picking_type_return).do_produce()

        # Checking child order data
        self.assertTrue(mrp_production1.child_order_id)
        self.assertEqual(len(mrp_production1.child_order_id.move_lines), 4)
        self.assertIn((self.product1, 4),
                      [(move.product_id, move.product_uom_qty) for move in mrp_production1.child_order_id.move_lines])
        self.assertIn((self.product2, 10),
                      [(move.product_id, move.product_uom_qty) for move in mrp_production1.child_order_id.move_lines])
        self.assertIn((self.product3, 2),
                      [(move.product_id, move.product_uom_qty) for move in mrp_production1.child_order_id.move_lines])
        self.assertIn((self.product3, 5),
                      [(move.product_id, move.product_uom_qty) for move in mrp_production1.child_order_id.move_lines])

        # Checking return picking data
        picking = self.env['stock.picking'].search([('picking_type_id', '=', self.stock_picking_type_return.id)])
        self.assertEqual(len(picking.move_lines), 2)
        self.assertIn((self.product1, 4), [(move.product_id, move.product_uom_qty) for move in picking.move_lines])
        self.assertIn((self.product3, 2), [(move.product_id, move.product_uom_qty) for move in picking.move_lines])

    def test_80_incomplete_production(self):
        """Same test as previous one, but we product less than required in the initial manufacturing order."""

        def create_service_move(move, qty):
            new_move = self.env['stock.move'].create({
                'name': "Service move for move %s" % move.name,
                'product_id': move.product_id.id,
                'product_uom_qty': qty,
                'product_uom': self.unit.id,
                'move_dest_id': move.id,
                'location_id': self.browse_ref('stock.stock_location_suppliers').id,
                'location_dest_id': move.location_id.id,
            })
            new_move.action_assign()
            new_move.action_done()

        mrp_production1, move1, move2, move3 = self.production_check(product_qty=2)
        self.assertFalse(self.env['stock.quant'].search([('product_id', '=', self.product_to_manufacture1.id)]))
        self.assertFalse(self.env['stock.quant'].search([('product_id', '=', self.product1.id)]))
        self.assertFalse(self.env['stock.quant'].search([('product_id', '=', self.product2.id)]))
        self.assertFalse(self.env['stock.quant'].search([('product_id', '=', self.product3.id)]))
        # Creation of service moves
        create_service_move(move1, 5)
        create_service_move(move3, 20)

        # Let's check that the manufactirng order becomes ready when quants are reserved but not any move is assigned.
        mrp_production1.action_assign()
        self.assertEqual(mrp_production1.state, 'ready')
        create_service_move(move1, 5)
        move1.action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(move2.state, 'confirmed')
        self.assertFalse(move2.reserved_quant_ids)
        self.assertEqual(move3.state, 'confirmed')
        self.assertEqual(len(move3.reserved_quant_ids), 1)
        self.assertEqual(move3.reserved_quant_ids.qty, 20)

        mrp_product_produce1_data = {
            'production_id': mrp_production1.id,
            'consume_lines': [(0, 0, vals) for vals in mrp_production1._calculate_qty(mrp_production1)]
        }
        mrp_product_produce1 = self.env['mrp.product.produce'].with_context({'active_id': mrp_production1.id}). \
            create(mrp_product_produce1_data)

        self.assertTrue(mrp_product_produce1.create_child)
        self.assertTrue(mrp_product_produce1.return_raw_materials)
        mrp_product_produce1.return_location_id = self.return_location.id
        self.assertEqual(len(mrp_product_produce1.consume_lines), 2)
        self.assertEqual(mrp_product_produce1.product_qty, 2)
        self.assertIn(self.product1, [cl.product_id for cl in mrp_product_produce1.consume_lines])
        self.assertNotIn(self.product2, [cl.product_id for cl in mrp_product_produce1.consume_lines])
        self.assertIn(self.product3, [cl.product_id for cl in mrp_product_produce1.consume_lines])
        for line in mrp_product_produce1.consume_lines:
            if line.product_id == self.product1:
                self.assertEqual(line.product_qty, 10)
            elif line.product_id == self.product3:
                self.assertEqual(line.product_qty, 20)

        # Let's decrease product_qty
        result = mrp_product_produce1.on_change_qty(product_qty=1, consume_lines=False)
        self.assertTrue(result.get('value') and result['value'].get('consume_lines'))
        result = result['value']['consume_lines']
        self.assertEqual(len(result), 2)
        self.assertIn([0, False, {'lot_id': False, 'product_id': self.product1.id, 'product_qty': 5.0}], result)
        self.assertIn([0, False, {'lot_id': False, 'product_id': self.product3.id, 'product_qty': 15.0}], result)

        # Let's increase product_qty. The system should not offer to consume more than reserved
        result = mrp_product_produce1.on_change_qty(product_qty=1.5, consume_lines=False)
        self.assertTrue(result.get('value') and result['value'].get('consume_lines'))
        result = result['value']['consume_lines']
        self.assertEqual(len(result), 2)
        self.assertIn([0, False, {'lot_id': False, 'product_id': self.product1.id, 'product_qty': 7.5}], result)
        self.assertIn([0, False, {'lot_id': False, 'product_id': self.product3.id, 'product_qty': 20.0}], result)

        # Let's go over the quantity oof the manufacturing order
        result = mrp_product_produce1.on_change_qty(product_qty=3, consume_lines=False)
        self.assertTrue(result.get('value') and result['value'].get('consume_lines'))
        result = result['value']['consume_lines']
        self.assertEqual(len(result), 2)
        self.assertIn([0, False, {'lot_id': False, 'product_id': self.product1.id, 'product_qty': 10.0}], result)
        self.assertIn([0, False, {'lot_id': False, 'product_id': self.product3.id, 'product_qty': 20.0}], result)
