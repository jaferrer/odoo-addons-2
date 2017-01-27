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

from openerp.tests import common
from openerp import exceptions


class TestPurchaseReceptionByOrder(common.TransactionCase):
    def setUp(self):
        super(TestPurchaseReceptionByOrder, self).setUp()
        self.test_product_1 = self.browse_ref('purchase_reception_by_order_line.test_product_1')
        self.test_product_2 = self.browse_ref('purchase_reception_by_order_line.test_product_2')
        self.test_product_3 = self.browse_ref('purchase_reception_by_order_line.test_product_3')
        self.stock_location_a = self.browse_ref('stock_performance_improved.stock_location_a')
        self.stock_location_b = self.browse_ref('stock_performance_improved.stock_location_b')
        self.order_1 = self.browse_ref('purchase_reception_by_order_line.order_1')
        self.order_line_1 = self.browse_ref('purchase_reception_by_order_line.order_line_1')
        self.order_line_2 = self.browse_ref('purchase_reception_by_order_line.order_line_2')
        self.order_line_3 = self.browse_ref('purchase_reception_by_order_line.order_line_3')
        self.order_2 = self.browse_ref('purchase_reception_by_order_line.order_2')
        self.order_line_4 = self.browse_ref('purchase_reception_by_order_line.order_line_4')
        self.unit = self.browse_ref('product.product_uom_unit')
        self.supplier = self.browse_ref('stock.stock_location_suppliers')
        self.stock = self.browse_ref('stock.stock_location_stock')
        self.picking_type_id = self.ref("stock.picking_type_internal")

    def get_picking_moves(self):
        [move1, move2, move3] = [False] * 3
        self.order_1.signal_workflow('purchase_confirm')
        self.assertEqual(len(self.order_1.picking_ids), 1)
        picking1 = self.order_1.picking_ids
        self.assertEqual(len(picking1.move_lines), 3)
        for move in picking1.move_lines:
            if move.purchase_line_id == self.order_line_1:
                move1 = move
            elif move.purchase_line_id == self.order_line_2:
                move2 = move
            elif move.purchase_line_id == self.order_line_3:
                move3 = move
        self.assertTrue(move1 and move2 and move3)
        return picking1, move1, move2, move3

    def check_packops(self, picking):
        self.assertEqual(len(picking.pack_operation_ids), 3)
        [packop1, packop2, packop3] = [False] * 3
        for packop in picking.pack_operation_ids:
            if packop.product_id == self.test_product_1 and packop.purchase_line_id == self.order_line_1:
                packop1 = packop
            elif packop.product_id == self.test_product_1 and packop.purchase_line_id == self.order_line_2:
                packop2 = packop
            elif packop.product_id == self.test_product_2:
                packop3 = packop
        self.assertTrue(packop1 and packop2 and packop3)
        return packop1, packop2, packop3

    def check_items(self, wizard):
        self.assertEqual(len(wizard.item_ids), 3)
        [item1, item2, item3] = [False] * 3
        for item in wizard.item_ids:
            if item.product_id == self.test_product_1 and item.purchase_line_id == self.order_line_1:
                item1 = item
            elif item.product_id == self.test_product_1 and item.purchase_line_id == self.order_line_2:
                item2 = item
            elif item.product_id == self.test_product_2:
                item3 = item
        self.assertTrue(item1 and item2 and item3)
        return item1, item2, item3

    def test_10_transfer_orders_one_by_one(self):
        picking1, _, _, _ = self.get_picking_moves()
        self.order_2.signal_workflow('purchase_confirm')
        picking1.do_prepare_partial()
        self.assertEqual(len(picking1.pack_operation_ids), 3)
        self.assertEqual(len(self.order_2.picking_ids), 1)

        # It should be impossible to receive lines of different orders at the same time
        wizard_id = picking1.do_enter_transfer_details()['res_id']
        wizard = self.env['stock.transfer_details'].browse(wizard_id)
        self.assertEqual(len(wizard.item_ids), 3)
        self.env['stock.transfer_details_items'].create({
            'transfer_id': wizard.id,
            'product_id': self.test_product_1.id,
            'quantity': 40,
            'product_uom_id': self.unit.id,
            'purchase_line_id': self.order_line_4.id,
            'sourceloc_id': self.supplier.id,
            'destinationloc_id': self.stock.id,
        })
        with self.assertRaises(exceptions.except_orm):
            wizard.do_detailed_transfer()
        with self.assertRaises(exceptions.except_orm):
            self.env['stock.pack.operation'].create({
                'picking_id': picking1.id,
                'product_id': self.test_product_1.id,
                'product_qty': 40,
                'product_uom_id': self.unit.id,
                'purchase_line_id': self.order_line_4.id,
                'location_id': self.supplier.id,
                'location_dest_id': self.stock.id,
            })

    def test_15_transfer_one_product_on_two_order_lines(self):
        picking1, move1, move2, _ = self.get_picking_moves()
        picking1.do_prepare_partial()
        self.assertEqual(len(picking1.pack_operation_ids), 3)

        wizard_id = picking1.do_enter_transfer_details()['res_id']
        wizard = self.env['stock.transfer_details'].browse(wizard_id)
        self.assertEqual(len(wizard.item_ids), 3)
        item1 = item2 = False
        for item in wizard.item_ids:
            if item.purchase_line_id == self.order_line_1:
                item1 = item
            if item.purchase_line_id == self.order_line_2:
                item2 = item
        item1.quantity = 10
        item2.quantity = 20
        wizard.do_detailed_transfer()

        packop1, packop2, _ = self.check_packops(picking1)

        self.assertEqual(packop1.product_qty, 10)
        self.assertEqual(packop2.product_qty, 20)
        self.assertEqual(packop1.purchase_line_id, self.order_line_1)
        self.assertEqual(packop2.purchase_line_id, self.order_line_2)
        self.assertEqual(move1.state, 'done')
        self.assertEqual(move2.state, 'done')
        self.assertEqual(move1.product_qty, 10)
        self.assertEqual(move2.product_qty, 20)

    def test_20_forbidden_actions_on_products(self):
        picking1, _, _, _ = self.get_picking_moves()
        self.order_2.signal_workflow('purchase_confirm')
        picking1.do_prepare_partial()
        self.assertEqual(len(picking1.pack_operation_ids), 3)
        self.assertEqual(len(self.order_2.picking_ids), 1)

        # It should be impossible for an item to have a POL of a different product than its product
        wizard_id = picking1.do_enter_transfer_details()['res_id']
        wizard = self.env['stock.transfer_details'].browse(wizard_id)
        self.assertEqual(len(wizard.item_ids), 3)
        self.env['stock.transfer_details_items'].create({
            'transfer_id': wizard.id,
            'product_id': self.test_product_2.id,
            'quantity': 40,
            'product_uom_id': self.unit.id,
            'purchase_line_id': self.order_line_1.id,
            'sourceloc_id': self.supplier.id,
            'destinationloc_id': self.stock.id,
        })
        with self.assertRaises(exceptions.except_orm):
            wizard.do_detailed_transfer()
        with self.assertRaises(exceptions.except_orm):
            self.env['stock.pack.operation'].create({
                'picking_id': picking1.id,
                'product_id': self.test_product_2.id,
                'product_qty': 40,
                'product_uom_id': self.unit.id,
                'purchase_line_id': self.order_line_1.id,
                'location_id': self.supplier.id,
                'location_dest_id': self.stock.id,
            })

    def test_30_affect_extra_move_to_correct_line(self):
        picking1, move1, move2, move3 = self.get_picking_moves()
        existing_move_ids = self.env['stock.move'].search([]).ids
        move3.action_cancel()
        wizard_id = picking1.do_enter_transfer_details()['res_id']
        wizard = self.env['stock.transfer_details'].browse(wizard_id)
        self.assertEqual(len(wizard.item_ids), 2)
        self.env['stock.transfer_details_items'].create({
            'transfer_id': wizard.id,
            'product_id': self.test_product_2.id,
            'quantity': 10,
            'product_uom_id': self.unit.id,
            'purchase_line_id': False,
            'sourceloc_id': self.supplier.id,
            'destinationloc_id': self.stock.id,
        })
        wizard.do_detailed_transfer()
        packop1, packop2, packop3 = self.check_packops(picking1)
        # Check that packop3 was attached to order_line_3
        self.assertFalse(packop3.purchase_line_id)
        extra_move = picking1.move_lines.filtered(lambda move: move.id not in existing_move_ids)
        self.assertEqual(len(extra_move), 1)
        self.assertEqual(extra_move.product_uom_qty, 10)
        self.assertEqual(extra_move.purchase_line_id, self.order_line_3)

    def test_40_create_extra_move_on_requested_line(self):
        picking1, move1, move2, move3 = self.get_picking_moves()
        move2.action_cancel()
        picking1.do_prepare_partial()
        self.assertEqual(len(picking1.pack_operation_ids), 2)

        wizard_id = picking1.do_enter_transfer_details()['res_id']
        wizard = self.env['stock.transfer_details'].browse(wizard_id)
        self.assertEqual(len(wizard.item_ids), 2)
        self.env['stock.transfer_details_items'].create({
            'transfer_id': wizard.id,
            'product_id': self.test_product_1.id,
            'quantity': 40,
            'product_uom_id': self.unit.id,
            'purchase_line_id': self.order_line_2.id,
            'sourceloc_id': self.supplier.id,
            'destinationloc_id': self.stock.id,
        })
        wizard.do_detailed_transfer()
        self.assertEqual(len(self.order_line_2.move_ids), 2)
        new_move = self.order_line_2.move_ids.filtered(lambda move: move.state != 'cancel')
        self.assertEqual(len(new_move), 1)
        self.assertEqual(new_move.product_uom_qty, 40)
        self.assertEqual(new_move.purchase_line_id, self.order_line_2)

    def test_50_receive_more_than_forseen_on_line(self):
        picking1, move1, move2, move3 = self.get_picking_moves()
        wizard_id = picking1.do_enter_transfer_details()['res_id']
        wizard = self.env['stock.transfer_details'].browse(wizard_id)
        item1, item2, item3 = self.check_items(wizard)
        self.assertEqual(item2.quantity, 60)
        item2.quantity = 80
        self.env['stock.transfer_details_items'].create({
            'transfer_id': wizard.id,
            'product_id': self.test_product_1.id,
            'quantity': 40,
            'product_uom_id': self.unit.id,
            'purchase_line_id': self.order_line_2.id,
            'sourceloc_id': self.supplier.id,
            'destinationloc_id': self.stock.id,
        })
        wizard.do_detailed_transfer()
        self.assertEqual(len(self.order_line_1.move_ids), 1)
        self.assertEqual(self.order_line_1.move_ids.product_uom_qty, 100)
        self.assertEqual(self.order_line_1.move_ids.state, 'done')
        self.assertEqual(len(self.order_line_3.move_ids), 1)
        self.assertEqual(self.order_line_3.move_ids.product_uom_qty, 30)
        self.assertEqual(self.order_line_3.move_ids.state, 'done')
        self.assertEqual(len(self.order_line_2.move_ids), 3)
        self.assertIn((self.test_product_1, 60, 'done'),
                      [(move.product_id, move.product_uom_qty, move.state) for move in self.order_line_2.move_ids])
        self.assertIn((self.test_product_1, 20, 'done'),
                      [(move.product_id, move.product_uom_qty, move.state) for move in self.order_line_2.move_ids])
        self.assertIn((self.test_product_1, 40, 'done'),
                      [(move.product_id, move.product_uom_qty, move.state) for move in self.order_line_2.move_ids])

    def test_60_receive_less_than_forseen_on_line(self):
        picking1, move1, move2, move3 = self.get_picking_moves()
        wizard_id = picking1.do_enter_transfer_details()['res_id']
        wizard = self.env['stock.transfer_details'].browse(wizard_id)
        item1, item2, item3 = self.check_items(wizard)
        self.assertEqual(item2.quantity, 60)
        item2.quantity = 10
        self.env['stock.transfer_details_items'].create({
            'transfer_id': wizard.id,
            'product_id': self.test_product_1.id,
            'quantity': 40,
            'product_uom_id': self.unit.id,
            'purchase_line_id': self.order_line_2.id,
            'sourceloc_id': self.supplier.id,
            'destinationloc_id': self.stock.id,
        })
        wizard.do_detailed_transfer()

        # Let's check pack operations
        self.assertEqual(len(picking1.pack_operation_ids), 4)
        self.assertIn((self.test_product_1, self.order_line_1, 100),
                      [(op.product_id, op.purchase_line_id, op.product_qty) for op in picking1.pack_operation_ids])
        self.assertIn((self.test_product_1, self.order_line_2, 10),
                      [(op.product_id, op.purchase_line_id, op.product_qty) for op in picking1.pack_operation_ids])
        self.assertIn((self.test_product_1, self.order_line_2, 40),
                      [(op.product_id, op.purchase_line_id, op.product_qty) for op in picking1.pack_operation_ids])
        self.assertIn((self.test_product_2, self.order_line_3, 30),
                      [(op.product_id, op.purchase_line_id, op.product_qty) for op in picking1.pack_operation_ids])

        # Let's check backorder
        backorder = self.env['stock.picking'].search([('backorder_id', '=', picking1.id)])
        self.assertEqual(len(backorder), 1)
        self.assertEqual(len(backorder.move_lines), 1)
        self.assertEqual(backorder.move_lines.product_uom_qty, 10)
        self.assertEqual(backorder.move_lines.product_id, self.test_product_1)
        self.assertEqual(backorder.move_lines.purchase_line_id, self.order_line_2)

        self.assertEqual(len(self.order_line_1.move_ids), 1)
        self.assertEqual(self.order_line_1.move_ids.product_uom_qty, 100)
        self.assertEqual(self.order_line_1.move_ids.state, 'done')
        self.assertEqual(len(self.order_line_2.move_ids), 2)
        self.assertIn((50, picking1, 'done'), [(move.product_uom_qty, move.picking_id, move.state) for
                                               move in self.order_line_2.move_ids])
        self.assertIn((10, backorder), [(move.product_uom_qty, move.picking_id) for move in self.order_line_2.move_ids])
        self.assertEqual(len(self.order_line_3.move_ids), 1)
        self.assertEqual(self.order_line_3.move_ids.product_uom_qty, 30)
        self.assertEqual(self.order_line_3.move_ids.state, 'done')

    def test_70_check_operation_links(self):

        move1 = self.env['stock.move'].create({
            'name': "Test move for product 1",
            'product_id': self.test_product_1.id,
            'product_uom_qty': 10,
            'picking_type_id': self.picking_type_id,
            'location_id': self.stock_location_a.id,
            'location_dest_id': self.stock_location_b.id,
            'product_uom': self.unit.id,
        })

        supply_move_product1 = self.env['stock.move'].create({
            'name': "Supply move for product 1",
            'product_id': self.test_product_1.id,
            'product_uom_qty': 10,
            'picking_type_id': self.picking_type_id,
            'location_id': self.supplier.id,
            'location_dest_id': self.stock_location_a.id,
            'product_uom': self.unit.id,
            'move_dest_id': move1.id,
        })

        move3 = self.env['stock.move'].create({
            'name': "Test move for product 4",
            'product_id': self.test_product_3.id,
            'product_uom_qty': 20,
            'picking_type_id': self.picking_type_id,
            'location_id': self.stock_location_a.id,
            'location_dest_id': self.stock_location_b.id,
            'product_uom': self.unit.id,
        })

        move1.action_confirm()
        move3.action_confirm()
        supply_move_product1.action_assign()
        supply_move_product1.action_done()

        picking = move1.picking_id
        self.assertTrue(picking)
        self.assertEqual(move3.picking_id, picking)

        picking.action_assign()
        picking.do_prepare_partial()

        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(move3.state, 'assigned')

        for move in [move1, move3]:
            self.assertEqual(len(move.linked_move_operation_ids), 1)

        for packop in picking.pack_operation_ids:
            self.assertEqual(len(packop.linked_move_operation_ids), 1)
