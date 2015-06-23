# -*- coding: utf8 -*-
#
#    Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

class TestPurchaseProcurementJIT(common.TransactionCase):

    def setUp(self):
        super(TestPurchaseProcurementJIT, self).setUp()
        self.supplier1 = self.browse_ref('purchase_procurement_just_in_time.supplier1')
        self.product1 = self.browse_ref('purchase_procurement_just_in_time.product1')
        self.product2 = self.browse_ref('purchase_procurement_just_in_time.product2')
        self.supplierinfo1 = self.browse_ref('purchase_procurement_just_in_time.supplierinfo1')
        self.supplierinfo2 = self.browse_ref('purchase_procurement_just_in_time.supplierinfo2')

        self.procurement_order_1 = self.env['procurement.order'].create({
            'name': 'Procurement order 1 (Purchase Procurement JIT)',
            'product_id': self.product1.id,
            'product_qty': 7,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock.stock_location_stock'),
            'date_planned': '2015-05-04 15:00:00',
            'product_uom': self.ref('product.product_uom_unit'),
        })

        self.procurement_order_2 = self.env['procurement.order'].create({
            'name': 'Procurement order 2 (Purchase Procurement JIT)',
            'product_id': self.product1.id,
            'product_qty': 40,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock.stock_location_stock'),
            'date_planned': '2015-05-04 15:00:00',
            'product_uom': self.ref('product.product_uom_unit'),
        })

        self.procurement_order_4 = self.env['procurement.order'].create({
            'name': 'Procurement order 4 (Purchase Procurement JIT)',
            'product_id': self.product2.id,
            'product_qty': 10,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock.stock_location_stock'),
            'date_planned': '2015-05-04 15:00:00',
            'product_uom': self.ref('product.product_uom_unit'),
        })

    def test_10_purchase_procurement_jit(self):

        """
        Testing calculation of opmsg_reduce_qty, to_delete and remaining_qty
        """

        self.procurement_order_1.run()
        self.assertTrue(self.procurement_order_1.rule_id.action == 'buy')
        self.assertTrue(self.procurement_order_1.purchase_line_id)
        self.procurement_order_2.run()
        self.assertTrue(self.procurement_order_2.rule_id.action == 'buy')
        purchase_order_1 = self.procurement_order_1.purchase_id
        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(len(purchase_order_1.order_line), 1)
        line = purchase_order_1.order_line[0]
        self.assertEqual(len(line.procurement_ids), 2)
        self.assertIn(self.procurement_order_1, line.procurement_ids)
        self.assertIn(self.procurement_order_2, line.procurement_ids)
        self.assertEqual(line.product_qty, 48)
        self.assertEqual(len(purchase_order_1.order_line), 1)
        self.assertIn(line, purchase_order_1.order_line)
        self.assertEqual(line.remaining_qty, 48)
        self.procurement_order_2.cancel()
        self.assertEqual(line.opmsg_reduce_qty, 36)
        self.assertEqual(line.product_qty, 48)
        self.procurement_order_1.cancel()
        self.assertEqual(line.opmsg_reduce_qty, 0)
        self.assertTrue(line.to_delete)
        move = [x for x in line.move_ids if x.product_qty == 7]
        self.assertEqual(len(move), 1)
        move = move[0]
        move.force_assign()
        move.action_done()
        self.assertEqual(line.remaining_qty, 41)

    def test_20_purchase_procurement_jit(self):

        """
        Testing calculation of opmsg_type, opmsg_delay and opmsg_text
        """

        self.procurement_order_1.run()
        self.assertTrue(self.procurement_order_1.rule_id.action == 'buy')
        self.assertTrue(self.procurement_order_1.purchase_line_id)
        self.procurement_order_2.run()
        self.assertTrue(self.procurement_order_2.rule_id.action == 'buy')
        purchase_order_1 = self.procurement_order_1.purchase_id
        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(len(purchase_order_1.order_line), 1)
        line = purchase_order_1.order_line[0]
        self.assertEqual(len(line.procurement_ids), 2)
        self.assertIn(self.procurement_order_1, line.procurement_ids)
        self.assertIn(self.procurement_order_2, line.procurement_ids)
        self.assertEqual(line.product_qty, 48)
        self.assertEqual(len(purchase_order_1.order_line), 1)
        self.assertIn(line, purchase_order_1.order_line)
        self.assertEqual(line.opmsg_delay, 0)
        self.assertEqual(line.opmsg_text, 'LATE by 0 day(s)')
        self.assertEqual(line.opmsg_type, 'late')
        line.date_planned = '2015-04-30 15:00:00'
        self.assertEqual(line.opmsg_delay, 1)
        self.assertEqual(line.opmsg_text, 'EARLY by 1 day(s)')
        self.assertEqual(line.opmsg_type, 'early')
        line.date_planned = '2015-05-02 15:00:00'
        self.assertEqual(line.opmsg_delay, 1)
        self.assertEqual(line.opmsg_text, 'LATE by 1 day(s)')
        self.assertEqual(line.opmsg_type, 'late')

    def test_30_purchase_procurement_jit(self):

        """
        Test canceling procurements of a draft purchase order line
        """

        self.procurement_order_1.run()
        self.procurement_order_2.run()
        self.procurement_order_4.run()
        self.assertEqual(self.procurement_order_1.purchase_id, self.procurement_order_2.purchase_id, self.procurement_order_4.purchase_id)
        purchase_order_1 = self.procurement_order_1.purchase_id
        purchase_order_1_id = purchase_order_1.id
        self.assertEqual(len(purchase_order_1.order_line), 2)
        line1 = False
        line2 = False
        for line in purchase_order_1.order_line:
            if line.product_id == self.product1:
                line1 = line
            if line.product_id == self.product2:
                line2 = line
        self.assertTrue(line1 and line2)
        self.procurement_order_2.cancel()
        self.assertEqual(line1.product_qty, 36)
        self.procurement_order_1.cancel()
        self.assertEqual(len(purchase_order_1.order_line), 1)
        self.assertIn(line2, purchase_order_1.order_line)
        self.procurement_order_4.cancel()
        self.assertFalse(self.env['purchase.order'].search([('id', '=', purchase_order_1_id)]))

    def test_40_purchase_procurement_jit(self):

        """
        Quantity of a draft purchase order line set to 0
        """

        self.procurement_order_1.run()
        self.procurement_order_2.run()
        procurement_order_3 = self.browse_ref('purchase_procurement_just_in_time.procurement_order_3')
        procurement_order_3.run()
        self.assertEqual(self.procurement_order_1.purchase_id, self.procurement_order_2.purchase_id, procurement_order_3.purchase_id)
        purchase_order_1 = self.procurement_order_1.purchase_id
        self.assertEqual(len(purchase_order_1.order_line), 1)
        line = False
        line = purchase_order_1.order_line[0]
        self.assertTrue(line)
        self.assertEqual(line.product_qty, 108)

        line.write({'product_qty': 0})

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(len(purchase_order_1.order_line), 1)
        self.assertIn(line, purchase_order_1.order_line)
        self.assertEqual(len(line.move_ids), 3)
        for move in line.move_ids:
            self.assertEqual(move.product_qty, 0)

    def test_50_purchase_procurement_jit(self):

        """
        Test increasing quantity a draft purchase order line
        """

        self.procurement_order_1.run()
        self.procurement_order_2.run()
        procurement_order_3 = self.browse_ref('purchase_procurement_just_in_time.procurement_order_3')
        procurement_order_3.run()
        self.assertEqual(self.procurement_order_1.purchase_id, self.procurement_order_2.purchase_id, procurement_order_3.purchase_id)
        purchase_order_1 = self.procurement_order_1.purchase_id
        self.assertEqual(len(purchase_order_1.order_line), 1)
        line = False
        line = purchase_order_1.order_line[0]
        self.assertTrue(line)
        self.assertEqual(line.product_qty, 108)

        line.write({'product_qty': 110})

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(len(purchase_order_1.order_line), 1)
        self.assertIn(line, purchase_order_1.order_line)
        self.assertEqual(len(line.move_ids), 4)
        [m1, m2, m3, m4] = [False]*4
        for move in line.move_ids:
            if move.product_qty == 7:
                m1 = move
            if move.product_qty == 40:
                m2 = move
            if move.product_qty == 50:
                m3 = move
            if move.product_qty == 13:
                m4 = move
        self.assertTrue(m1 and m2 and m3 and m4)
        self.assertEqual(m1.procurement_id, self.procurement_order_1)
        self.assertEqual(m1.state, 'assigned')
        self.assertEqual(m2.procurement_id, self.procurement_order_2)
        self.assertEqual(m2.state, 'assigned')
        self.assertEqual(m3.procurement_id, procurement_order_3)
        self.assertEqual(m3.state, 'assigned')
        self.assertEqual(m4.procurement_id, self.env['procurement.order'])
        self.assertEqual(m4.state, 'assigned')

    def test_60_purchase_procurement_jit(self):

        """
        Test decreasing quantity a draft purchase order line with 3 move needed
        """

        self.procurement_order_1.run()
        self.procurement_order_2.run()

        procurement_order_3 = self.env['procurement.order'].create({
            'name': 'Procurement order 3 (Purchase Procurement JIT)',
            'product_id': self.product1.id,
            'product_qty': 50,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock.stock_location_stock'),
            'date_planned': '2015-05-04 15:00:00',
            'product_uom': self.ref('product.product_uom_unit'),
        })

        procurement_order_3.run()
        self.assertEqual(self.procurement_order_1.purchase_id, self.procurement_order_2.purchase_id, procurement_order_3.purchase_id)
        purchase_order_1 = self.procurement_order_1.purchase_id
        self.assertEqual(len(purchase_order_1.order_line), 1)
        line = False
        line = purchase_order_1.order_line[0]
        self.assertTrue(line)
        self.assertEqual(line.product_qty, 108)

        line.write({'product_qty': 90})

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(len(purchase_order_1.order_line), 1)
        self.assertIn(line, purchase_order_1.order_line)
        self.assertEqual(len(line.move_ids), 3)
        [m1, m2, m3] = [False] * 3
        for move in line.move_ids:
            if move.product_qty == 7:
                m1 = move
            if move.product_qty == 40:
                m2 = move
            if move.product_qty == 43:
                m3 = move
        self.assertTrue(m1 and m2 and m3)
        self.assertEqual(m1.procurement_id, self.procurement_order_1)
        self.assertEqual(m1.state, 'assigned')
        self.assertEqual(m2.procurement_id, self.procurement_order_2)
        self.assertEqual(m2.state, 'assigned')
        self.assertEqual(m3.procurement_id, procurement_order_3)
        self.assertEqual(m3.state, 'assigned')

    def test_70_purchase_procurement_jit(self):

        """
        Test decreasing quantity a draft purchase order line with 2 move needed (the 3rd has a null quantity)
        """

        self.procurement_order_1.run()
        self.procurement_order_2.run()

        procurement_order_3 = self.env['procurement.order'].create({
            'name': 'Procurement order 3 (Purchase Procurement JIT)',
            'product_id': self.product1.id,
            'product_qty': 50,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock.stock_location_stock'),
            'date_planned': '2015-05-04 15:00:00',
            'product_uom': self.ref('product.product_uom_unit'),
        })

        procurement_order_3.run()
        self.assertEqual(self.procurement_order_1.purchase_id, self.procurement_order_2.purchase_id, procurement_order_3.purchase_id)
        purchase_order_1 = self.procurement_order_1.purchase_id
        self.assertEqual(len(purchase_order_1.order_line), 1)
        line = False
        line = purchase_order_1.order_line[0]
        self.assertTrue(line)
        self.assertEqual(line.product_qty, 108)

        line.write({'product_qty': 45})

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(len(purchase_order_1.order_line), 1)
        self.assertIn(line, purchase_order_1.order_line)
        self.assertEqual(len(line.move_ids), 3)
        [m1, m2, m3] = [False] * 3
        for move in line.move_ids:
            if move.product_qty == 7:
                m1 = move
            if move.product_qty == 38:
                m2 = move
            if move.product_qty == 0:
                m3 = move
        self.assertTrue(m1 and m2 and m3)
        self.assertEqual(m1.procurement_id, self.procurement_order_1)
        self.assertEqual(m1.state, 'assigned')
        self.assertEqual(m2.procurement_id, self.procurement_order_2)
        self.assertEqual(m2.state, 'assigned')
        self.assertEqual(m3.procurement_id, procurement_order_3)
        self.assertEqual(m3.state, 'assigned')
        for move in [m1, m2, m3]:
            self.assertTrue(move.picking_id)
            self.assertTrue(move.picking_type_id)
        picking = m1.picking_id
        self.assertTrue(m2 in picking.move_lines and m3 in picking.move_lines)
        picking.force_assign()
        transfer = picking.do_enter_transfer_details()
        transfer_details = self.env['stock.transfer_details'].browse(transfer['res_id'])
        transfer_details.do_detailed_transfer()
        self.assertEqual(m1.state, 'done')
        self.assertEqual(m2.state, 'done')
        self.assertEqual(m3.state, 'done')

    def test_80_purchase_procurement_jit(self):

        """
        Decreasing line quantity of a confirmed purchase order line
        """

        def test_decreasing_line_qty(line, new_qty, number_moves, list_quantities):
                line.write({'product_qty': new_qty})
                self.assertEqual(len(line.move_ids), number_moves)
                for item in list_quantities:
                    self.assertIn(item, [x.product_qty for x in line.move_ids])
                for item in line.move_ids:
                    if item.product_qty == 0 and item.procurement_id:
                        self.assertNotEqual(item.state, 'cancel')

        def test_procurement_id(list_moves_procurements):
            for item in list_moves_procurements:
                if item[1]:
                    self.assertEqual(item[0].procurement_id, item[1])
                else:
                    self.assertEqual(item[0].procurement_id, self.env['procurement.order'])

        self.procurement_order_1.run()
        self.procurement_order_2.run()
        procurement_order_3 = self.browse_ref('purchase_procurement_just_in_time.procurement_order_3')
        procurement_order_3.run()
        self.assertEqual(self.procurement_order_1.purchase_id, self.procurement_order_2.purchase_id, procurement_order_3.purchase_id)
        purchase_order_1 = self.procurement_order_1.purchase_id
        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(len(purchase_order_1.order_line), 1)
        line = purchase_order_1.order_line[0]

        [m1, m2, m3, m4] = [False]*4
        for move in line.move_ids:
            if move.product_qty == 7:
                m1 = move
            if move.product_qty == 40:
                m2 = move
            if move.product_qty == 50:
                m3 = move
            if move.product_qty == 11:
                m4 = move
        self.assertTrue(m1 and m2 and m3 and m4)

        test_decreasing_line_qty(line, 106, 4, [7,40,50,9])
        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3], [m4, False]])
        test_decreasing_line_qty(line, 98, 4, [7,40,50,1])
        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3], [m4, False]])
        test_decreasing_line_qty(line, 97, 3, [7,40,50])
        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3]])
        self.assertEqual(m4.state, 'cancel')
        test_decreasing_line_qty(line, 96, 3, [7,40,49])
        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3]])
        test_decreasing_line_qty(line, 48, 3, [7,40,1])
        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3]])
        test_decreasing_line_qty(line, 47, 3, [7,39,1])
        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3]])
        test_decreasing_line_qty(line, 46, 3, [7,38,1])
        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3]])
        test_decreasing_line_qty(line, 16, 3, [7,8,1])
        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3]])
        test_decreasing_line_qty(line, 15, 3, [7,7,1])
        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3]])
        test_decreasing_line_qty(line, 14, 3, [6,7,1])
        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3]])
        test_decreasing_line_qty(line, 13, 3, [6,6,1])
        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3]])
        test_decreasing_line_qty(line, 6, 3, [0,5,1])
        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3]])
        test_decreasing_line_qty(line, 1, 3, [0,0,1])

    def test_90_purchase_procurement_jit(self):

        """
        Increasing quantity of a confirmed purchase order line
        """

        def test_increasing_line_qty(line, new_qty, number_moves, list_moves_quantities):
                line.write({'product_qty': new_qty})
                self.assertEqual(len(line.move_ids), number_moves)
                for item in list_moves_quantities:
                    self.assertEqual(item[0].product_qty, item[1])

        def test_procurement_id(list_moves_procurements):
            for item in list_moves_procurements:
                if item[1]:
                    self.assertEqual(item[0].procurement_id, item[1])
                else:
                    self.assertEqual(item[0].procurement_id, self.env['procurement.order'])

        self.procurement_order_1.run()
        self.procurement_order_2.run()
        procurement_order_3 = self.browse_ref('purchase_procurement_just_in_time.procurement_order_3')
        procurement_order_3.run()
        self.assertEqual(self.procurement_order_1.purchase_id, self.procurement_order_2.purchase_id, procurement_order_3.purchase_id)
        purchase_order_1 = self.procurement_order_1.purchase_id
        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(len(purchase_order_1.order_line), 1)
        line = purchase_order_1.order_line[0]

        [m1, m2, m3, m4] = [False]*4
        for move in line.move_ids:
            if move.product_qty == 7:
                m1 = move
            if move.product_qty == 40:
                m2 = move
            if move.product_qty == 50:
                m3 = move
            if move.product_qty == 11:
                m4 = move
        self.assertTrue(m1 and m2 and m3 and m4)

        # first: with one move without procurement_id

        test_increasing_line_qty(line, 109, 4, [[m1,7], [m2,40], [m3,50], [m4,12]])
        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3], [m4, False]])
        test_increasing_line_qty(line, 110, 4, [[m1,7], [m2,40], [m3,50], [m4,13]])
        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3], [m4, False]])
        test_increasing_line_qty(line, 210, 4, [[m1,7], [m2,40], [m3,50], [m4,113]])
        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3], [m4, False]])
        for move in [m1, m2, m3, m4]:
            self.assertTrue(move.picking_id)
            self.assertTrue(move.picking_type_id)
        picking = m1.picking_id
        self.assertTrue(m2 in picking.move_lines and m3 in picking.move_lines and m4 in picking.move_lines)

        # next: every move has a not-False procurement_id (after deletion of m4)

        line.write({'product_qty': 97})
        self.assertEqual(len(line.move_ids), 3)
        self.assertIn(7, [x.product_qty for x in line.move_ids])
        self.assertIn(40, [x.product_qty for x in line.move_ids])
        self.assertIn(50, [x.product_qty for x in line.move_ids])
        self.assertIn(m1, line.move_ids)
        self.assertIn(m2, line.move_ids)
        self.assertIn(m3, line.move_ids)

        m4 = False
        test_increasing_line_qty(line, 109, 4, [[m1,7], [m2,40], [m3,50]])
        for move in line.move_ids:
            if move not in [m1,m3,m3]:
                m4 = move
        self.assertTrue(m4)

        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3], [m4, False]])
        test_increasing_line_qty(line, 110, 4, [[m1,7], [m2,40], [m3,50], [m4,13]])
        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3], [m4, False]])
        test_increasing_line_qty(line, 210, 4, [[m1,7], [m2,40], [m3,50], [m4,113]])
        test_procurement_id([[m1, self.procurement_order_1], [m2, self.procurement_order_2], [m3, procurement_order_3], [m4, False]])
        for move in [m1, m2, m3, m4]:
            self.assertTrue(move.picking_id)
            self.assertTrue(move.picking_type_id)
        picking = m1.picking_id
        self.assertTrue(m2 in picking.move_lines and m3 in picking.move_lines and m4 in picking.move_lines)

    def test_100_purchase_procurement_jit(self):

        """
        Testing draft purchase order lines splits
        """

        self.procurement_order_1.run()
        self.procurement_order_2.run()
        self.assertEqual(self.procurement_order_1.purchase_id, self.procurement_order_2.purchase_id)
        purchase_order_1 = self.procurement_order_1.purchase_id
        self.assertEqual(len(purchase_order_1.order_line), 1)
        line = purchase_order_1.order_line[0]
        self.assertEqual(line.product_qty, 48)

        split = self.env['split.line'].create({'line_id': line.id, 'qty': 20})
        split.do_split()
        self.assertEqual(len(purchase_order_1.order_line), 2)
        self.assertIn(line, purchase_order_1.order_line)
        line2 = [l for l in purchase_order_1.order_line if l != line][0]
        self.assertEqual(line2.father_line_id, line)
        self.assertEqual(line.children_number, 1)
        self.assertEqual(line2.line_no, '10 - 1')
        self.assertEqual(line2.product_qty, 28)

        split = self.env['split.line'].create({'line_id': line2.id, 'qty': 10})
        split.do_split()
        self.assertEqual(len(purchase_order_1.order_line), 3)
        self.assertIn(line, purchase_order_1.order_line)
        self.assertIn(line2, purchase_order_1.order_line)
        line3 = [l for l in purchase_order_1.order_line if l not in [line, line2]][0]
        self.assertEqual(line3.father_line_id, line)
        self.assertEqual(line.children_number, 2)
        self.assertEqual(line3.line_no, '10 - 2')
        self.assertEqual(line3.product_qty, 18)

        split = self.env['split.line'].create({'line_id': line.id, 'qty': 5})
        split.do_split()
        self.assertEqual(len(purchase_order_1.order_line), 4)
        self.assertIn(line, purchase_order_1.order_line)
        self.assertIn(line2, purchase_order_1.order_line)
        self.assertIn(line3, purchase_order_1.order_line)
        line1 = [l for l in purchase_order_1.order_line if l not in [line, line2, line3]][0]
        self.assertEqual(line1.father_line_id, line)
        self.assertEqual(line.children_number, 3)
        self.assertEqual(line1.line_no, '10 - 3')
        self.assertEqual(line1.product_qty, 15)

        purchase_order_1.signal_workflow('purchase_confirm')

        self.assertEqual(len(line.move_ids), 2)
        [m1, m2] = [False]*2
        for move in line.move_ids:
            if move.product_qty == 5:
                m1 = move
            if move.product_qty == 0:
                m2 = move
        self.assertTrue(m1 and m2)
        self.assertEqual(m1.procurement_id, self.procurement_order_1)
        self.assertEqual(m2.procurement_id, self.procurement_order_2)
        self.assertEqual(len(line1.move_ids), 1)
        self.assertEqual(line1.move_ids[0].product_qty, 15)
        self.assertEqual(len(line2.move_ids), 1)
        self.assertEqual(line2.move_ids[0].product_qty, 10)
        self.assertEqual(len(line3.move_ids), 1)
        self.assertEqual(line3.move_ids[0].product_qty, 18)

    def test_110_purchase_procurement_jit(self):

        """
        Testing confirmed purchase order lines splits
        """

        self.procurement_order_1.run()
        self.procurement_order_2.run()
        self.assertEqual(self.procurement_order_1.purchase_id, self.procurement_order_2.purchase_id)
        purchase_order_1 = self.procurement_order_1.purchase_id
        self.assertEqual(len(purchase_order_1.order_line), 1)
        line = purchase_order_1.order_line[0]
        self.assertEqual(line.product_qty, 48)

        purchase_order_1.signal_workflow('purchase_confirm')

        split = self.env['split.line'].create({'line_id': line.id, 'qty': 20})
        split.do_split()
        self.assertEqual(len(purchase_order_1.order_line), 2)
        self.assertIn(line, purchase_order_1.order_line)
        line2 = [l for l in purchase_order_1.order_line if l != line][0]
        self.assertEqual(line2.father_line_id, line)
        self.assertEqual(line.children_number, 1)
        self.assertEqual(line2.line_no, '10 - 1')
        self.assertEqual(line2.product_qty, 28)

        split = self.env['split.line'].create({'line_id': line2.id, 'qty': 10})
        split.do_split()
        self.assertEqual(len(purchase_order_1.order_line), 3)
        self.assertIn(line, purchase_order_1.order_line)
        self.assertIn(line2, purchase_order_1.order_line)
        line3 = [l for l in purchase_order_1.order_line if l not in [line, line2]][0]
        self.assertEqual(line3.father_line_id, line)
        self.assertEqual(line.children_number, 2)
        self.assertEqual(line3.line_no, '10 - 2')
        self.assertEqual(line3.product_qty, 18)

        split = self.env['split.line'].create({'line_id': line.id, 'qty': 5})
        split.do_split()
        self.assertEqual(len(purchase_order_1.order_line), 4)
        self.assertIn(line, purchase_order_1.order_line)
        self.assertIn(line2, purchase_order_1.order_line)
        self.assertIn(line3, purchase_order_1.order_line)
        line1 = [l for l in purchase_order_1.order_line if l not in [line, line2, line3]][0]
        self.assertEqual(line1.father_line_id, line)
        self.assertEqual(line.children_number, 3)
        self.assertEqual(line1.line_no, '10 - 3')
        self.assertEqual(line1.product_qty, 15)

        self.assertEqual(len(line.move_ids), 2)
        [m1, m2] = [False]*2
        for move in line.move_ids:
            if move.product_qty == 1:
                m1 = move
            if move.product_qty == 4:
                m2 = move
        self.assertTrue(m1 and m2)
        self.assertEqual(m1.procurement_id, self.env['procurement.order'])
        self.assertEqual(m2.procurement_id, self.procurement_order_1)

        self.assertEqual(len(line1.move_ids), 2)
        [m1, m2] = [False]*2
        for move in line1.move_ids:
            if move.product_qty == 3:
                m1 = move
            if move.product_qty == 12:
                m2 = move
        self.assertTrue(m1 and m2)
        self.assertEqual(m1.procurement_id, self.procurement_order_1)
        self.assertEqual(m2.procurement_id, self.procurement_order_2)

        self.assertEqual(len(line2.move_ids), 1)
        self.assertEqual(line2.move_ids[0].product_qty, 10)
        self.assertEqual(line2.move_ids[0].procurement_id, self.procurement_order_2)

        self.assertEqual(len(line3.move_ids), 1)
        self.assertEqual(line3.move_ids[0].product_qty, 18)
        self.assertEqual(line2.move_ids[0].procurement_id, self.procurement_order_2)
