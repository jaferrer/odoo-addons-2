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

    def production_check(self):
        mrp_production1 = self.env['mrp.production'].create({
            'name': 'mrp_production1',
            'product_id': self.product_to_manufacture1.id,
            'product_qty': 1,
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
        for move in mrp_production1.move_lines:
            if move.product_qty == 5:
                move1 = move
            if move.product_qty == 10:
                move2 = move
            if move.product_qty == 15:
                move3 = move
        self.assertTrue(move1)
        self.assertTrue(move2)
        self.assertTrue(move3)
        return mrp_production1, move1, move2, move3

    def test_10_incomplete_production(self):
        """Test with one move available: move1"""
        mrp_production1, move1, move2, move3 = self.production_check()
        move1.force_assign()
        self.assertEquals(move1.state, 'assigned')
        mrp_production1.action_assign()
        self.assertEqual(mrp_production1.state, 'ready')
        mrp_product_produce1_data = {
            'production_id': mrp_production1.id,
            'consume_lines': [(0, 0, vals) for vals in mrp_production1._calculate_qty(mrp_production1)]
        }
        mrp_product_produce1 = self.env['mrp.product.produce'].with_context({'active_id': mrp_production1.id}).\
                                                                                    create(mrp_product_produce1_data)
        self.assertEqual(len(mrp_product_produce1.consume_lines), 1)
        self.assertEqual(mrp_product_produce1.consume_lines[0].product_id, self.product1)
        self.assertEqual(mrp_product_produce1.consume_lines[0].product_qty, self.line1.product_qty)
        self.assertEqual(mrp_product_produce1.child_src_loc_id, mrp_production1.location_src_id)
        self.assertEqual(mrp_product_produce1.child_src_loc_id, mrp_production1.location_src_id)
        self.assertEqual(mrp_product_produce1.child_dest_loc_id, mrp_production1.location_dest_id)
        self.assertEqual(mrp_product_produce1.child_production_product_id, mrp_production1.product_id)

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
        move1.force_assign()
        self.assertEquals(move1.state, 'assigned')
        move2.force_assign()
        self.assertEquals(move2.state, 'assigned')
        mrp_production1.action_assign()
        self.assertEqual(mrp_production1.state, 'ready')
        mrp_product_produce1_data = {
            'production_id': mrp_production1.id,
            'consume_lines': [(0, 0, vals) for vals in mrp_production1._calculate_qty(mrp_production1)]
        }
        mrp_product_produce1 = self.env['mrp.product.produce'].with_context({'active_id': mrp_production1.id}).\
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
        move1.force_assign()
        mrp_production1.action_ready()
        self.assertEqual(mrp_production1.state, 'ready')
        mrp_product_produce1_data = {
            'production_id': mrp_production1.id,
            'consume_lines': [(0, 0, vals) for vals in mrp_production1._calculate_qty(mrp_production1)]
        }
        mrp_product_produce1 = self.env['mrp.product.produce'].with_context({'active_id': mrp_production1.id}).\
                                                                            create(mrp_product_produce1_data)
        mrp_product_produce1.do_produce()
        self.assertEqual(mrp_production1.state, 'done')
        self.assertEqual(len(mrp_production1.child_move_ids), 2)
        self.assertTrue(mrp_production1.child_order_id)
        mrp_production2 = mrp_production1.child_order_id

        list_move = [x for x in mrp_production2.move_lines if x.product_id == self.product2]
        self.assertEqual(len(list_move), 1)
        move = list_move[0]
        move.force_assign()
        mrp_production2.action_ready()
        self.assertEqual(mrp_production2.state, 'ready')
        mrp_product_produce2_data = {
            'production_id': mrp_production2.id,
            'consume_lines': [(0, 0, vals) for vals in mrp_production2._calculate_qty(mrp_production2)]
        }
        mrp_product_produce2 = self.env['mrp.product.produce'].with_context({'active_id': mrp_production2.id}).\
                                                                            create(mrp_product_produce2_data)
        mrp_product_produce2.do_produce()
        self.assertEqual(mrp_production2.state, 'done')
        self.assertEqual(len(mrp_production2.child_move_ids), 1)
        self.assertTrue(mrp_production2.child_order_id)
        mrp_production3 = mrp_production2.child_order_id

        self.assertEqual(len(mrp_production3.move_lines), 1)
        move = mrp_production3.move_lines[0]
        self.assertEqual(move.product_id, self.product3)
        move.force_assign()
        mrp_production3.action_ready()
        self.assertEqual(mrp_production3.state, 'ready')
        mrp_product_produce3_data = {
            'production_id': mrp_production3.id,
            'consume_lines': [(0, 0, vals) for vals in mrp_production3._calculate_qty(mrp_production3)]
        }
        mrp_product_produce3 = self.env['mrp.product.produce'].with_context({'active_id': mrp_production3.id}).\
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
        move1.force_assign()
        mrp_production1.action_ready()
        self.assertEqual(mrp_production1.state, 'ready')
        mrp_product_produce1_data = {
            'production_id': mrp_production1.id,
            'consume_lines': [(0, 0, vals) for vals in mrp_production1._calculate_qty(mrp_production1)]
        }
        mrp_product_produce1 = self.env['mrp.product.produce'].with_context({'active_id': mrp_production1.id}).\
                                                                            create(mrp_product_produce1_data)
        mrp_product_produce1.do_produce()
        self.assertTrue(mrp_production1.child_order_id)
        mrp_production2 = mrp_production1.child_order_id
        self.assertEqual(mrp_production2.product_id, self.product_to_manufacture1)
        mrp_production2.button_update()
        self.assertEqual(len(mrp_production2.move_lines), 2)
