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

from openerp import exceptions
from openerp.tests import common


class TestPurchaseProcurementJIT(common.TransactionCase):

    def setUp(self):
        super(TestPurchaseProcurementJIT, self).setUp()
        self.supplier1 = self.browse_ref('purchase_procurement_just_in_time.supplier1')
        self.product1 = self.browse_ref('purchase_procurement_just_in_time.product1')
        self.product2 = self.browse_ref('purchase_procurement_just_in_time.product2')
        self.product3 = self.browse_ref('purchase_procurement_just_in_time.product3')
        self.supplierinfo1 = self.browse_ref('purchase_procurement_just_in_time.supplierinfo1')
        self.supplierinfo2 = self.browse_ref('purchase_procurement_just_in_time.supplierinfo2')
        self.location_a = self.browse_ref('purchase_procurement_just_in_time.stock_location_a')
        self.location_b = self.browse_ref('purchase_procurement_just_in_time.stock_location_b')
        self.warehouse = self.browse_ref('stock.warehouse0')
        self.unit = self.browse_ref('product.product_uom_unit')
        self.uom_couple = self.browse_ref('purchase_procurement_just_in_time.uom_couple')
        self.uom_four = self.browse_ref('purchase_procurement_just_in_time.uom_four')

    def create_procurement_order_1(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 1 (Purchase Procurement JIT)',
            'product_id': self.product1.id,
            'product_qty': 7,
            'warehouse_id': self.warehouse.id,
            'location_id': self.location_a.id,
            'date_planned': '3003-05-04 15:00:00',
            'product_uom': self.ref('product.product_uom_unit'),
        })

    def create_procurement_order_2(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 2 (Purchase Procurement JIT)',
            'product_id': self.product1.id,
            'product_qty': 40,
            'warehouse_id': self.warehouse.id,
            'location_id': self.location_a.id,
            'date_planned': '3003-05-04 15:00:00',
            'product_uom': self.ref('product.product_uom_unit'),
        })

    def create_procurement_order_3(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 3 (Purchase Procurement JIT)',
            'product_id': self.product1.id,
            'product_qty': 50,
            'warehouse_id': self.warehouse.id,
            'location_id': self.location_a.id,
            'date_planned': '3003-05-04 15:00:00',
            'product_uom': self.ref('product.product_uom_unit'),
        })

    def create_procurement_order_4(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 4 (Purchase Procurement JIT)',
            'product_id': self.product2.id,
            'product_qty': 8,
            'warehouse_id': self.warehouse.id,
            'location_id': self.location_b.id,
            'date_planned': '3003-05-09 15:00:00',
            'product_uom': self.ref('product.product_uom_unit'),
        })

    def create_procurement_order_5(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 5 (Purchase Procurement JIT)',
            'product_id': self.product3.id,
            'product_qty': 13,
            'warehouse_id': self.warehouse.id,
            'location_id': self.location_a.id,
            'date_planned': '3003-05-18 15:00:00',
            'product_uom': self.ref('product.product_uom_unit'),
        })

    def create_and_run_proc_1_2_4(self):
        procurement_order_1 = self.create_procurement_order_1()
        procurement_order_1.run()
        self.assertEqual(procurement_order_1.state, 'buy_to_run')
        procurement_order_2 = self.create_procurement_order_2()
        procurement_order_2.run()
        self.assertEqual(procurement_order_2.state, 'buy_to_run')
        procurement_order_4 = self.create_procurement_order_4()
        procurement_order_4.run()
        self.assertEqual(procurement_order_4.state, 'running')
        proc5 = self.env['procurement.order'].search(
            [('move_dest_id', 'in', procurement_order_4.move_ids.ids)])
        self.assertEqual(len(proc5), 1)
        proc5.run()
        self.assertEqual(proc5.state, 'buy_to_run')

        self.env['procurement.order'].purchase_schedule(jobify=False)
        self.assertTrue(procurement_order_1.purchase_id)
        self.assertEqual(procurement_order_1.purchase_id, procurement_order_2.purchase_id)
        self.assertEqual(procurement_order_1.purchase_id, proc5.purchase_id)
        return procurement_order_1, procurement_order_2, proc5

    def create_and_run_proc_1_2_3(self):
        procurement_order_1 = self.create_procurement_order_1()
        procurement_order_1.run()
        self.assertEqual(procurement_order_1.state, 'buy_to_run')
        procurement_order_2 = self.create_procurement_order_2()
        procurement_order_2.run()
        self.assertEqual(procurement_order_2.state, 'buy_to_run')
        procurement_order_3 = self.create_procurement_order_3()
        procurement_order_3.run()
        self.assertEqual(procurement_order_3.state, 'buy_to_run')
        self.env['procurement.order'].purchase_schedule(jobify=False)
        self.assertTrue(procurement_order_1.purchase_id)
        self.assertEqual(procurement_order_1.purchase_id, procurement_order_2.purchase_id)
        self.assertEqual(procurement_order_1.purchase_id, procurement_order_3.purchase_id)
        return procurement_order_1, procurement_order_2, procurement_order_3

    def create_and_run_proc_1_2(self):
        procurement_order_1 = self.create_procurement_order_1()
        procurement_order_1.run()
        self.assertEqual(procurement_order_1.state, 'buy_to_run')
        procurement_order_2 = self.create_procurement_order_2()
        procurement_order_2.run()
        self.assertEqual(procurement_order_2.state, 'buy_to_run')
        self.env['procurement.order'].purchase_schedule(jobify=False)
        self.assertEqual(procurement_order_1.purchase_id, procurement_order_2.purchase_id)
        return procurement_order_1, procurement_order_2

    def check_purchase_order_1_2_4(self, purchase_order_1):
        self.assertEqual(len(purchase_order_1.order_line), 2)
        line1 = False
        line2 = False
        for line in purchase_order_1.order_line:
            if line.product_id == self.product1:
                line1 = line
            if line.product_id == self.product2:
                line2 = line
        self.assertTrue(line1 and line2)
        self.assertEqual(line1.product_qty, 48)
        self.assertEqual(line2.product_qty, 10)
        self.assertEqual(purchase_order_1.state, 'draft')
        return line1, line2

    def check_purchase_order_1_2_3(self, purchase_order):
        self.assertEqual(len(purchase_order.order_line), 1)
        line = purchase_order.order_line[0]
        self.assertTrue(line)
        self.assertEqual(line.product_qty, 108)
        return line

    def check_purchase_order_1_2(self, purchase_order):
        self.assertEqual(len(purchase_order.order_line), 1)
        line = purchase_order.order_line[0]
        self.assertEqual(line.product_qty, 48)
        return line

    def test_05_purchase_procurement_jit(self):
        """
        Testing calculation of opmsg_reduce_qty, to_delete and remaining_qty
        """
        # procurement_order_1 = self.create_procurement_order_1()
        # procurement_order_1.run()
        # self.assertTrue(procurement_order_1.rule_id.action == 'buy')
        # self.assertTrue(procurement_order_1.purchase_line_id)
        # procurement_order_2 = self.create_procurement_order_2()
        # procurement_order_2.run()
        # self.assertTrue(procurement_order_2.rule_id.action == 'buy')
        # purchase_order_1 = procurement_order_1.purchase_id
        # purchase_order_1.signal_workflow('purchase_confirm')
        # self.assertEqual(len(purchase_order_1.order_line), 1)
        # line = purchase_order_1.order_line[0]
        # self.assertEqual(len(line.procurement_ids), 2)
        # self.assertIn(procurement_order_1, line.procurement_ids)
        # self.assertIn(procurement_order_2, line.procurement_ids)
        # self.assertEqual(line.product_qty, 48)
        # self.assertEqual(len(purchase_order_1.order_line), 1)
        # self.assertIn(line, purchase_order_1.order_line)
        # self.assertEqual(line.remaining_qty, 48)
        #
        # procurement_order_2.cancel()
        # self.assertEqual(line.opmsg_reduce_qty, 36)
        # self.assertEqual(line.product_qty, 48)
        #
        # procurement_order_1.cancel()
        # self.assertEqual(line.opmsg_reduce_qty, 0)
        # self.assertTrue(line.to_delete)

    def test_10_purchase_procurement_jit(self):
        """
        Testing calculation of opmsg_type, opmsg_delay and opmsg_text
        """
        # procurement_order_1 = self.create_procurement_order_1()
        # procurement_order_1.run()
        # self.assertTrue(procurement_order_1.rule_id.action == 'buy')
        # self.assertTrue(procurement_order_1.purchase_line_id)
        # procurement_order_2 = self.create_procurement_order_2()
        # procurement_order_2.run()
        # self.assertTrue(procurement_order_2.rule_id.action == 'buy')
        # purchase_order_1 = procurement_order_1.purchase_id
        # purchase_order_1.signal_workflow('purchase_confirm')
        # self.assertEqual(len(purchase_order_1.order_line), 1)
        # line = purchase_order_1.order_line[0]
        # self.assertEqual(len(line.procurement_ids), 2)
        # self.assertIn(procurement_order_1, line.procurement_ids)
        # self.assertIn(procurement_order_2, line.procurement_ids)
        # self.assertEqual(line.product_qty, 48)
        # self.assertEqual(len(purchase_order_1.order_line), 1)
        # self.assertIn(line, purchase_order_1.order_line)
        # self.assertEqual(line.opmsg_delay, 0)
        #
        # if self.env.user.lang == 'fr_FR':
        #     self.assertEqual(line.opmsg_text, u"EN RETARD de 0 jour(s)")
        # else:
        #     self.assertEqual(line.opmsg_text, "LATE by 0 day(s)")
        #
        # self.assertEqual(line.opmsg_type, 'late')
        # line.date_planned = '2015-04-30 15:00:00'
        # self.assertEqual(line.opmsg_delay, 1)
        # if self.env.user.lang == 'fr_FR':
        #     self.assertEqual(line.opmsg_text, u"EN AVANCE de 1 jour(s)")
        # else:
        #     self.assertEqual(line.opmsg_text, "EARLY by 1 day(s)")
        # self.assertEqual(line.opmsg_type, 'early')
        # line.date_planned = '2015-05-02 15:00:00'
        # self.assertEqual(line.opmsg_delay, 1)
        # if self.env.user.lang == 'fr_FR':
        #     self.assertEqual(line.opmsg_text, u"EN RETARD de 1 jour(s)")
        # else:
        #     self.assertEqual(line.opmsg_text, "LATE by 1 day(s)")
        # self.assertEqual(line.opmsg_type, 'late')

    def test_15_purchase_procurement_jit(self):
        """
        Test canceling procurements of a draft purchase order line
        """
        procurement_order_1, procurement_order_2, procurement_order_4 = self.create_and_run_proc_1_2_4()
        purchase_order_1 = procurement_order_1.purchase_id
        line1, line2 = self.check_purchase_order_1_2_4(purchase_order_1)

        # Check that cancelling procurements makes no difference on the draft purchase order
        procurement_order_2.cancel()
        self.assertEqual(line1.product_qty, 48)
        procurement_order_1.cancel()
        self.assertEqual(len(purchase_order_1.order_line), 2)
        self.assertEqual(line1.product_qty, 48)
        self.assertEqual(line2.product_qty, 10)
        procurement_order_4.cancel()
        self.assertEqual(len(purchase_order_1.order_line), 2)
        self.assertEqual(line1.product_qty, 48)
        self.assertEqual(line2.product_qty, 10)

        # Now let's run the purchase scheduler again
        # We recreate proc 1 and check that we keep the same PO
        new_proc_1 = self.create_procurement_order_1()
        new_proc_1.run()
        self.assertEqual(new_proc_1.state, 'buy_to_run')

        self.env['procurement.order'].purchase_schedule(jobify=False)
        self.assertEqual(len(purchase_order_1.order_line), 1)
        self.assertEqual(purchase_order_1.order_line[0].product_qty, 36)
        self.assertEqual(purchase_order_1.order_line[0].product_id, self.product1)

        self.assertEqual(procurement_order_1.state, 'cancel')
        self.assertEqual(procurement_order_2.state, 'cancel')
        self.assertEqual(procurement_order_4.state, 'cancel')

    def test_17_purchase_procurement_jit(self):
        """
        Test proc exception when no supplier
        """
        proc = self.create_procurement_order_5()
        proc.run()
        self.assertEqual(proc.state, 'exception')

    def test_20_purchase_procurement_jit(self):
        """
        Test canceling procurements of a not-draft purchase order line (simple case)
        """
        procurement_order_1, procurement_order_2, procurement_order_4 = self.create_and_run_proc_1_2_4()
        purchase_order_1 = procurement_order_1.purchase_id
        line1, line2 = self.check_purchase_order_1_2_4(purchase_order_1)

        # Let's confirm our purchase order
        def check_purchase_order_with_procs():
            self.assertEqual(purchase_order_1.state, 'approved')

            self.assertEqual(len(line1.move_ids), 3)
            self.assertIn([7, procurement_order_1, 'assigned'],
                          [[x.product_uom_qty, x.procurement_id, x.state] for x in line1.move_ids])
            self.assertIn([40, procurement_order_2, 'assigned'],
                          [[x.product_uom_qty, x.procurement_id, x.state] for x in line1.move_ids])
            self.assertIn([1, self.env['procurement.order'], 'assigned'],
                          [[x.product_uom_qty, x.procurement_id, x.state] for x in line1.move_ids])
            self.assertEqual(len(line2.move_ids), 2)
            m1 = m2 = self.env['stock.move']
            for m in line2.move_ids:
                if m.product_uom_qty == 8:
                    m1 = m
                elif m.product_uom_qty == 2:
                    m2 = m
            self.assertEqual(m1.state, 'assigned')
            self.assertEqual(m1.procurement_id.id, line2.procurement_ids.id)
            self.assertEqual(m1.move_dest_id, line2.procurement_ids.move_dest_id)
            self.assertEqual(m1.move_dest_id.state, "waiting")
            self.assertEqual(m2.state, 'assigned')
            self.assertFalse(m2.procurement_id)
            self.assertTrue(m2.move_dest_id)
            self.assertEqual(m2.move_dest_id.state, "waiting")
            self.assertEqual(line2.product_qty, 10)
            self.assertEqual(line2.procurement_ids, procurement_order_4)

            self.assertEqual(len(line1.order_id.picking_ids), 1)
            picking_recpt = line1.order_id.picking_ids
            self.assertEqual(len(picking_recpt.move_lines), 5)
            self.assertIn([7, self.product1, procurement_order_1, 'assigned'],
                          [[x.product_uom_qty, x.product_id, x.procurement_id, x.state] for x in
                           picking_recpt.move_lines])
            self.assertIn([40, self.product1, procurement_order_2, 'assigned'],
                          [[x.product_uom_qty, x.product_id, x.procurement_id, x.state] for x in
                           picking_recpt.move_lines])
            self.assertIn([1, self.product1, self.env['procurement.order'], 'assigned'],
                          [[x.product_uom_qty, x.product_id, x.procurement_id, x.state] for x in
                           picking_recpt.move_lines])
            self.assertIn([8, self.product2, procurement_order_4, 'assigned'],
                          [[x.product_uom_qty, x.product_id, x.procurement_id, x.state] for x in
                           picking_recpt.move_lines])
            self.assertIn([2, self.product2, self.env['procurement.order'], 'assigned'],
                          [[x.product_uom_qty, x.product_id, x.procurement_id, x.state] for x in
                           picking_recpt.move_lines])

        def check_purchase_order_without_procs():
            self.assertEqual(purchase_order_1.state, 'approved')

            self.assertEqual(len(line1.move_ids), 3)
            self.assertIn([7, self.env['procurement.order'], 'assigned'],
                          [[x.product_uom_qty, x.procurement_id, x.state] for x in line1.move_ids])
            self.assertIn([40, self.env['procurement.order'], 'assigned'],
                          [[x.product_uom_qty, x.procurement_id, x.state] for x in line1.move_ids])
            self.assertIn([1, self.env['procurement.order'], 'assigned'],
                          [[x.product_uom_qty, x.procurement_id, x.state] for x in line1.move_ids])

            self.assertEqual(len(line2.move_ids), 2)
            m1 = m2 = self.env['stock.move']
            for m in line2.move_ids:
                if m.product_uom_qty == 8:
                    m1 = m
                elif m.product_uom_qty == 2:
                    m2 = m
            self.assertEqual(m1.state, 'assigned')
            self.assertFalse(m1.procurement_id.id)
            self.assertTrue(m1.move_dest_id)
            self.assertEqual(m1.move_dest_id.state, "waiting")
            self.assertEqual(m2.state, 'assigned')
            self.assertFalse(m2.procurement_id)
            self.assertTrue(m2.move_dest_id)
            self.assertEqual(m2.move_dest_id.state, "waiting")

            self.assertEqual(len(line1.order_id.picking_ids), 1)
            picking_recpt = line1.order_id.picking_ids
            self.assertEqual(len(picking_recpt.move_lines), 5)
            self.assertIn([7, self.product1, self.env['procurement.order'], 'assigned'],
                          [[x.product_uom_qty, x.product_id, x.procurement_id, x.state] for x in
                           picking_recpt.move_lines])
            self.assertIn([40, self.product1, self.env['procurement.order'], 'assigned'],
                          [[x.product_uom_qty, x.product_id, x.procurement_id, x.state] for x in
                           picking_recpt.move_lines])
            self.assertIn([1, self.product1, self.env['procurement.order'], 'assigned'],
                          [[x.product_uom_qty, x.product_id, x.procurement_id, x.state] for x in
                           picking_recpt.move_lines])
            self.assertIn([8, self.product2, self.env['procurement.order'], 'assigned'],
                          [[x.product_uom_qty, x.product_id, x.procurement_id, x.state] for x in
                           picking_recpt.move_lines])
            self.assertIn([2, self.product2, self.env['procurement.order'], 'assigned'],
                          [[x.product_uom_qty, x.product_id, x.procurement_id, x.state] for x in
                           picking_recpt.move_lines])

        purchase_order_1.signal_workflow('purchase_confirm')
        check_purchase_order_with_procs()

        # Check that cancelling the purchase order does not change anything
        procurement_order_2.cancel()
        procurement_order_1.cancel()
        procurement_order_4.cancel()
        check_purchase_order_without_procs()

        # Check that after rescheduling we still have our PO unchanged, but no more procurements attached
        self.env['procurement.order'].purchase_schedule(jobify=False)
        check_purchase_order_without_procs()
        self.assertEqual(procurement_order_1.state, 'cancel')
        self.assertEqual(procurement_order_2.state, 'cancel')
        self.assertEqual(procurement_order_4.state, 'cancel')

    def test_25_purchase_procurement_jit(self):
        """
        Trying to cancel a procurement with other procurements received in the line.
        """
        procurement_order_1, procurement_order_2, procurement_order_4 = self.create_and_run_proc_1_2_4()
        purchase_order_1 = procurement_order_1.purchase_id
        line1, line2 = self.check_purchase_order_1_2_4(purchase_order_1)

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(purchase_order_1.state, 'approved')

        self.assertEqual(len(line1.move_ids), 3)
        self.assertIn([7, procurement_order_1, 'assigned'],
                      [[x.product_uom_qty, x.procurement_id, x.state] for x in line1.move_ids])
        self.assertIn([40, procurement_order_2, 'assigned'],
                      [[x.product_uom_qty, x.procurement_id, x.state] for x in line1.move_ids])
        self.assertIn([1, self.env['procurement.order'], 'assigned'],
                      [[x.product_uom_qty, x.procurement_id, x.state] for x in line1.move_ids])
        self.assertEqual(len(line2.move_ids), 2)
        m1 = m2 = self.env['stock.move']
        for m in line2.move_ids:
            if m.product_uom_qty == 8:
                m1 = m
            elif m.product_uom_qty == 2:
                m2 = m
        self.assertEqual(m1.state, 'assigned')
        self.assertEqual(m1.procurement_id.id, line2.procurement_ids.id)
        self.assertEqual(m1.move_dest_id, line2.procurement_ids.move_dest_id)
        self.assertEqual(m1.move_dest_id.state, "waiting")
        self.assertEqual(m2.state, 'assigned')
        self.assertFalse(m2.procurement_id)
        self.assertTrue(m2.move_dest_id)
        self.assertEqual(m2.move_dest_id.state, "waiting")

        [m1, m2, m3] = [False] * 3
        for move in line1.move_ids:
            if move.product_qty == 7:
                m1 = move
            if move.product_qty == 40:
                m2 = move
            if move.product_qty == 1:
                m3 = move
        self.assertTrue(m1 and m2 and m3)

        self.assertEqual(m1.procurement_id, procurement_order_1)
        self.assertEqual(m2.procurement_id, procurement_order_2)
        self.assertFalse(m3.procurement_id)

        m2.action_done()
        m3.action_done()

        procurement_order_1.cancel()

        self.assertEqual(len(line1.move_ids), 3)

        self.assertIn([40, procurement_order_2, 'done'],
                      [[x.product_uom_qty, x.procurement_id, x.state] for x in line1.move_ids])
        self.assertIn([1, self.env['procurement.order'], 'done'],
                      [[x.product_uom_qty, x.procurement_id, x.state] for x in line1.move_ids])
        self.assertIn([7, self.env['procurement.order'], 'assigned'],
                      [[x.product_uom_qty, x.procurement_id, x.state] for x in line1.move_ids])

    def test_30_purchase_procurement_jit(self):
        """
        Trying to cancel a procurement partially received.
        """
        procurement_order_1, procurement_order_2, procurement_order_4 = self.create_and_run_proc_1_2_4()
        purchase_order_1 = procurement_order_1.purchase_id
        line1, line2 = self.check_purchase_order_1_2_4(purchase_order_1)

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(purchase_order_1.state, 'approved')

        self.assertEqual(len(line1.move_ids), 3)
        self.assertIn([7, procurement_order_1, 'assigned'],
                      [[x.product_uom_qty, x.procurement_id, x.state] for x in line1.move_ids])
        self.assertIn([40, procurement_order_2, 'assigned'],
                      [[x.product_uom_qty, x.procurement_id, x.state] for x in line1.move_ids])
        self.assertIn([1, self.env['procurement.order'], 'assigned'],
                      [[x.product_uom_qty, x.procurement_id, x.state] for x in line1.move_ids])
        self.assertEqual(len(line2.move_ids), 2)
        m1 = m2 = self.env['stock.move']
        for m in line2.move_ids:
            if m.product_uom_qty == 8:
                m1 = m
            elif m.product_uom_qty == 2:
                m2 = m
        self.assertEqual(m1.state, 'assigned')
        self.assertEqual(m1.procurement_id.id, line2.procurement_ids.id)
        self.assertEqual(m1.move_dest_id, line2.procurement_ids.move_dest_id)
        self.assertEqual(m1.move_dest_id.state, "waiting")
        self.assertEqual(m2.state, 'assigned')
        self.assertFalse(m2.procurement_id)
        self.assertTrue(m2.move_dest_id)
        self.assertEqual(m2.move_dest_id.state, "waiting")

        [m1, m2, m3] = [False] * 3
        for move in line1.move_ids:
            if move.product_qty == 7:
                m1 = move
            if move.product_qty == 40:
                m2 = move
            if move.product_qty == 1:
                m3 = move
        self.assertTrue(m1 and m2 and m3)

        self.assertEqual(m1.procurement_id, procurement_order_1)
        self.assertEqual(m2.procurement_id, procurement_order_2)
        self.assertEqual(m2.purchase_line_id, line1)
        self.assertFalse(m3.procurement_id)

        m4 = self.env['stock.move'].browse(self.env['stock.move'].split(m2, 10))

        self.assertEqual(m4.procurement_id, procurement_order_2)
        m4.purchase_line_id = line1

        m4.action_done()
        procurement_order_2.cancel()

        self.assertEqual(procurement_order_2.state, 'cancel')
        self.assertEqual(procurement_order_2.product_qty, 30)
        self.assertNotIn(m4.procurement_id, [procurement_order_1, procurement_order_2, procurement_order_4])
        self.assertEqual(m4.procurement_id.product_qty, 10)
        self.assertEqual(m4.procurement_id.state, 'done')

        self.assertEqual(len(line1.move_ids), 4)
        self.assertIn([m4, 10, self.product1, m4.procurement_id, 'done'],
                      [[x, x.product_uom_qty, x.product_id, x.procurement_id, x.state] for x in line1.move_ids])
        self.assertIn([30, self.product1, self.env['procurement.order'], 'assigned'],
                      [[x.product_uom_qty, x.product_id, x.procurement_id, x.state] for x in line1.move_ids])
        self.assertIn([7, self.product1, procurement_order_1, 'assigned'],
                      [[x.product_uom_qty, x.product_id, x.procurement_id, x.state] for x in line1.move_ids])
        self.assertIn([1, self.product1, self.env['procurement.order'], 'assigned'],
                      [[x.product_uom_qty, x.product_id, x.procurement_id, x.state] for x in line1.move_ids])

        self.env['procurement.order'].purchase_schedule(jobify=False)
        self.assertEqual(procurement_order_2.state, 'cancel')
        self.assertEqual(procurement_order_2.product_qty, 30)
        self.assertNotIn(m4.procurement_id, [procurement_order_1, procurement_order_2, procurement_order_4])
        self.assertEqual(m4.procurement_id.product_qty, 10)
        self.assertEqual(m4.procurement_id.state, 'done')

    def test_35_purchase_procurement_jit(self):
        """
        Quantity of a draft purchase order line set to 0
        """
        procurement_order_1, procurement_order_2, procurement_order_3 = self.create_and_run_proc_1_2_3()
        purchase_order_1 = procurement_order_1.purchase_id
        line = self.check_purchase_order_1_2_3(purchase_order_1)

        line.write({'product_qty': 0})

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(len(purchase_order_1.order_line), 1)
        self.assertIn(line, purchase_order_1.order_line)
        self.assertEqual(len(line.move_ids), 0)

    def test_36_purchase_procurement_jit(self):
        """
        Draft purchase order line removed
        """
        procurement_order_1, procurement_order_2, procurement_order_4 = self.create_and_run_proc_1_2_4()
        purchase_order_1 = procurement_order_1.purchase_id
        line1, line2 = self.check_purchase_order_1_2_4(purchase_order_1)

        line2.unlink()

        self.assertEqual(len(purchase_order_1.order_line), 1)
        self.assertIn(line1, purchase_order_1.order_line)
        self.assertEqual(procurement_order_4.state, 'buy_to_run')

    def test_38_purchase_procurement_jit(self):
        """
        Manual purchase order manipulation
        """
        order = self.env['purchase.order'].create({
            'partner_id': self.supplier1.id,
            'location_id': self.location_a.id,
            'pricelist_id': self.ref('purchase.list0')
        })
        line = self.env['purchase.order.line'].create({
            'name': "product 1",
            'product_id': self.product1.id,
            'date_planned': "2016-12-01",
            'order_id': order.id,
            'price_unit': 2,
            'product_qty': 10,
        })
        order.signal_workflow('purchase_confirm')
        self.assertEqual(order.state, 'approved')
        self.assertEqual(line.move_ids[0].product_uom_qty, 10)
        line.product_qty = 11
        self.assertEqual(order.state, 'approved')
        self.assertEqual(line.move_ids[0].product_uom_qty, 11)
        line.product_qty = 9
        self.assertEqual(order.state, 'approved')
        self.assertEqual(line.move_ids[0].product_uom_qty, 9)

        picking = order.picking_ids[0]
        picking.do_prepare_partial()
        packop = self.env['stock.pack.operation'].search([('product_id', '=', self.product1.id),
                                                          ('picking_id', '=', picking.id)])
        packop.product_qty = 5
        picking.do_transfer()

        self.assertEqual(order.state, 'approved')
        self.assertEqual(len(line.move_ids), 2)
        self.assertIn((4, 'assigned'), [(m.product_uom_qty, m.state) for m in line.move_ids])
        self.assertIn((5, 'done'), [(m.product_uom_qty, m.state) for m in line.move_ids])

        line.product_qty = 5
        self.assertEqual(len(line.move_ids), 1)
        self.assertEqual(line.move_ids[0].product_uom_qty, 5)

    def test_40_purchase_procurement_jit(self):
        """
        Test increasing quantity a draft purchase order line
        """
        procurement_order_1, procurement_order_2, procurement_order_3 = self.create_and_run_proc_1_2_3()
        purchase_order_1 = procurement_order_1.purchase_id
        line = self.check_purchase_order_1_2_3(purchase_order_1)

        line.write({'product_qty': 110})

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(len(purchase_order_1.order_line), 1)
        self.assertIn(line, purchase_order_1.order_line)
        self.assertEqual(len(line.move_ids), 4)
        [m1, m2, m3, m4] = [False] * 4
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
        self.assertEqual(m1.procurement_id, procurement_order_1)
        self.assertEqual(m1.state, 'assigned')
        self.assertEqual(m2.procurement_id, procurement_order_2)
        self.assertEqual(m2.state, 'assigned')
        self.assertEqual(m3.procurement_id, procurement_order_3)
        self.assertEqual(m3.state, 'assigned')
        self.assertEqual(m4.procurement_id, self.env['procurement.order'])
        self.assertEqual(m4.state, 'assigned')

    def test_45_purchase_procurement_jit(self):
        """
        Test decreasing quantity a draft purchase order line with 3 move needed
        """
        procurement_order_1, procurement_order_2, procurement_order_3 = self.create_and_run_proc_1_2_3()
        purchase_order_1 = procurement_order_1.purchase_id
        line = self.check_purchase_order_1_2_3(purchase_order_1)

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
        self.assertEqual(m1.procurement_id, procurement_order_1)
        self.assertEqual(m1.state, 'assigned')
        self.assertEqual(m2.procurement_id, procurement_order_2)
        self.assertEqual(m2.state, 'assigned')
        self.assertFalse(m3.procurement_id)
        self.assertEqual(m3.state, 'assigned')

    def test_50_purchase_procurement_jit(self):
        """
        Test decreasing quantity a draft purchase order line with 2 move needed (the 3rd has a null quantity)
        """
        procurement_order_1, procurement_order_2, procurement_order_3 = self.create_and_run_proc_1_2_3()
        purchase_order_1 = procurement_order_1.purchase_id
        line = self.check_purchase_order_1_2_3(purchase_order_1)

        line.write({'product_qty': 45})

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(len(purchase_order_1.order_line), 1)
        self.assertIn(line, purchase_order_1.order_line)
        self.assertEqual(len(line.move_ids), 2)
        [m1, m2] = [False] * 2
        for move in line.move_ids:
            if move.product_qty == 7:
                m1 = move
            if move.product_qty == 38:
                m2 = move
        self.assertTrue(m1 and m2)
        self.assertEqual(m1.procurement_id, procurement_order_1)
        self.assertEqual(m1.state, 'assigned')
        self.assertFalse(m2.procurement_id)
        self.assertEqual(m2.state, 'assigned')
        for move in [m1, m2]:
            self.assertTrue(move.picking_id)
            self.assertTrue(move.picking_type_id)
        picking = m1.picking_id
        self.assertTrue(m2 in picking.move_lines)
        picking.force_assign()
        transfer = picking.do_enter_transfer_details()
        transfer_details = self.env['stock.transfer_details'].browse(transfer['res_id'])
        transfer_details.do_detailed_transfer()
        self.assertEqual(m1.state, 'done')
        self.assertEqual(m2.state, 'done')

    def test_55_purchase_procurement_jit(self):
        """
        Decreasing line quantity of a confirmed purchase order line
        """
        def test_decreasing_line_qty(line_tested, new_qty, number_moves, list_quantities):
            line_tested.write({'product_qty': new_qty})
            self.assertEqual(len(line_tested.move_ids), number_moves)
            for item in list_quantities:
                self.assertIn(item, [x.product_qty for x in line_tested.move_ids])

        def test_procurement_id(list_moves_procurements):
            for item in list_moves_procurements:
                if item[1]:
                    self.assertEqual(item[0].procurement_id, item[1])
                else:
                    self.assertEqual(item[0].procurement_id, self.env['procurement.order'])

        procurement_order_1, procurement_order_2, procurement_order_3 = self.create_and_run_proc_1_2_3()
        purchase_order_1 = procurement_order_1.purchase_id
        line = self.check_purchase_order_1_2_3(purchase_order_1)

        purchase_order_1.signal_workflow('purchase_confirm')

        self.assertEqual(len(line.move_ids), 4)
        [m1, m2, m3, m4] = [False] * 4
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

        test_decreasing_line_qty(line, 106, 4, [7, 40, 50, 9])
        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2], [m3, procurement_order_3]])
        test_decreasing_line_qty(line, 98, 4, [7, 40, 50, 1])
        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2], [m3, procurement_order_3]])
        test_decreasing_line_qty(line, 97, 3, [7, 40, 50])
        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2], [m3, procurement_order_3]])
        test_decreasing_line_qty(line, 96, 3, [7, 40, 49])
        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2]])
        test_decreasing_line_qty(line, 48, 3, [7, 40, 1])
        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2]])
        test_decreasing_line_qty(line, 47, 2, [7, 40])
        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2]])
        test_decreasing_line_qty(line, 46, 2, [7, 39])
        test_procurement_id([[m1, procurement_order_1]])
        test_decreasing_line_qty(line, 8, 2, [7, 1])
        test_procurement_id([[m1, procurement_order_1]])
        test_decreasing_line_qty(line, 7, 1, [7])
        test_decreasing_line_qty(line, 6, 1, [6])
        test_decreasing_line_qty(line, 0, 0, [])
        line.product_qty = 0
        self.assertFalse(line.move_ids.filtered(lambda m: m != 'cancel'))

    def test_56_purchase_procurement_jit(self):
        """
        Cancelling a confirmed purchase order
        """
        procurement_order_1, procurement_order_2, procurement_order_4 = self.create_and_run_proc_1_2_4()
        purchase_order_1 = procurement_order_1.purchase_id
        line1, line2 = self.check_purchase_order_1_2_4(purchase_order_1)

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(purchase_order_1.state, 'approved')
        self.assertEqual(line1.state, 'confirmed')
        self.assertEqual(line2.state, 'confirmed')

        self.assertEqual(len(line2.move_ids), 2)
        m1 = m2 = self.env['stock.move']
        for m in line2.move_ids:
            if m.product_uom_qty == 8:
                m1 = m
            elif m.product_uom_qty == 2:
                m2 = m
        self.assertEqual(m1.state, 'assigned')
        self.assertEqual(m1.procurement_id.id, line2.procurement_ids.id)
        m1_dest = m1.move_dest_id
        self.assertEqual(m1_dest, line2.procurement_ids.move_dest_id)
        self.assertEqual(m1_dest.state, "waiting")

        self.assertEqual(m2.state, 'assigned')
        self.assertFalse(m2.procurement_id)
        m2_dest = m2.move_dest_id
        self.assertTrue(m2_dest)
        self.assertEqual(m2_dest.state, "waiting")

        purchase_order_1.action_cancel()

        self.assertEqual(procurement_order_1.state, 'buy_to_run')
        self.assertEqual(procurement_order_2.state, 'buy_to_run')
        self.assertEqual(procurement_order_4.state, 'buy_to_run')

        m1 = self.env['stock.move'].search([('id', '=', m1.id)])
        m2 = self.env['stock.move'].search([('id', '=', m2.id)])
        self.assertEqual(m1.state, 'cancel')
        self.assertTrue(m1_dest)
        self.assertEqual(m1_dest.state, 'waiting')

        self.assertTrue(m2)
        self.assertEqual(m2.state, 'cancel')
        self.assertTrue(m2_dest)
        self.assertEqual(m2_dest.state, 'cancel')

    def test_57_purchase_procurement_jit(self):
        """
        Decreasing line quantity of a confirmed purchase order line with moves done
        """
        def test_decreasing_line_qty(line_tested, new_qty, number_moves, list_quantities):
            line_tested.write({'product_qty': new_qty})
            self.assertEqual(len(line_tested.move_ids), number_moves)
            for item in list_quantities:
                self.assertIn(item, [x.product_qty for x in line_tested.move_ids])

        def test_procurement_id(list_moves_procurements):
            for item in list_moves_procurements:
                if item[1]:
                    self.assertEqual(item[0].procurement_id, item[1])
                else:
                    self.assertEqual(item[0].procurement_id, self.env['procurement.order'])

        procurement_order_1, procurement_order_2, procurement_order_3 = self.create_and_run_proc_1_2_3()
        purchase_order_1 = procurement_order_1.purchase_id
        line = self.check_purchase_order_1_2_3(purchase_order_1)

        purchase_order_1.signal_workflow('purchase_confirm')

        self.assertEqual(len(line.move_ids), 4)
        [m1, m2, m3, m4] = [self.env['stock.move']] * 4
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

        picking = purchase_order_1.picking_ids[0]
        picking.do_prepare_partial()
        packop = self.env['stock.pack.operation'].search([('product_id', '=', self.product1.id),
                                                          ('picking_id', '=', picking.id)])
        packop.product_qty = 18
        picking.do_transfer()

        test_decreasing_line_qty(line, 106, 5, [7, 11, 29, 50, 9])
        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2], [m3, procurement_order_3]])
        test_decreasing_line_qty(line, 98, 5, [7, 11, 29, 50, 1])
        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2], [m3, procurement_order_3]])
        test_decreasing_line_qty(line, 97, 4, [7, 11, 29, 50])
        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2], [m3, procurement_order_3]])
        test_decreasing_line_qty(line, 96, 4, [7, 11, 29, 49])
        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2]])
        test_decreasing_line_qty(line, 48, 4, [7, 11, 29, 1])
        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2]])
        test_decreasing_line_qty(line, 47, 3, [7, 11, 29])
        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2]])
        test_decreasing_line_qty(line, 46, 3, [7, 11, 28])
        test_procurement_id([[m1, procurement_order_1]])
        test_decreasing_line_qty(line, 19, 3, [7, 11, 1])
        test_procurement_id([[m1, procurement_order_1]])
        test_decreasing_line_qty(line, 18, 2, [7, 11])
        self.assertRaises(exceptions.except_orm, test_decreasing_line_qty, line, 0, 1, [])
        self.assertFalse(line.move_ids.filtered(lambda m: m.state not in ['cancel', 'done']))

        # Let's run the scheduler to check that nothing changes
        self.env['procurement.order'].purchase_schedule(jobify=False)
        self.assertEqual(len(line.move_ids), 2)
        self.assertIn(11, [m.product_uom_qty for m in line.move_ids])
        self.assertIn(7, [m.product_uom_qty for m in line.move_ids])

        # Let's increase/decrease again to check
        self.assertEqual(line.order_id.state, 'except_picking')
        line.order_id.signal_workflow('picking_ok')
        self.assertEqual(line.order_id.state, 'approved')
        test_decreasing_line_qty(line, 19, 3, [7, 11, 1])
        test_decreasing_line_qty(line, 18, 2, [7, 11])

    def test_58_purchase_procurement_jit(self):
        """
        Deleting a draft purchase order
        """
        procurement_order_1, procurement_order_2, procurement_order_4 = self.create_and_run_proc_1_2_4()
        purchase_order_1 = procurement_order_1.purchase_id
        line1, line2 = self.check_purchase_order_1_2_4(purchase_order_1)

        self.assertEqual(purchase_order_1.state, 'draft')
        self.assertEqual(procurement_order_1.state, 'running')
        self.assertEqual(procurement_order_2.state, 'running')
        self.assertEqual(procurement_order_4.state, 'running')
        purchase_order_1.unlink()

        self.assertEqual(procurement_order_1.state, 'buy_to_run')
        self.assertEqual(procurement_order_2.state, 'buy_to_run')
        self.assertEqual(procurement_order_4.state, 'buy_to_run')

    def test_60_purchase_procurement_jit(self):
        """
        Increasing quantity of a confirmed purchase order line
        """
        def test_increasing_line_qty(line_tested, new_qty, number_moves, list_moves_quantities):
            line_tested.write({'product_qty': new_qty})
            self.assertEqual(len(line_tested.move_ids), number_moves)
            self.assertEqual(sum(m.product_uom_qty for m in line_tested.move_ids), new_qty)
            for item in list_moves_quantities:
                self.assertEqual(item[0].product_qty, item[1])

        def test_procurement_id(list_moves_procurements):
            for item in list_moves_procurements:
                if item[1]:
                    self.assertEqual(item[0].procurement_id, item[1])
                else:
                    self.assertEqual(item[0].procurement_id, self.env['procurement.order'])

        procurement_order_1, procurement_order_2, procurement_order_3 = self.create_and_run_proc_1_2_3()
        purchase_order_1 = procurement_order_1.purchase_id
        line = self.check_purchase_order_1_2_3(purchase_order_1)

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(purchase_order_1.state, 'approved')

        [m1, m2, m3, m4] = [False] * 4
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

        test_increasing_line_qty(line, 109, 4, [[m1, 7], [m2, 40], [m3, 50]])
        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2], [m3, procurement_order_3]])
        test_increasing_line_qty(line, 110, 4, [[m1, 7], [m2, 40], [m3, 50]])
        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2], [m3, procurement_order_3]])
        test_increasing_line_qty(line, 210, 4, [[m1, 7], [m2, 40], [m3, 50]])
        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2], [m3, procurement_order_3]])
        for move in [m1, m2, m3]:
            self.assertTrue(move.picking_id)
            self.assertTrue(move.picking_type_id)
        self.assertRaises(exceptions.MissingError, getattr, m4, 'name')
        picking = m1.picking_id
        self.assertTrue(m2 in picking.move_lines and m3 in picking.move_lines)

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
        test_increasing_line_qty(line, 109, 4, [[m1, 7], [m2, 40], [m3, 50]])
        for move in line.move_ids:
            if move not in [m1, m3, m3]:
                m4 = move
        self.assertTrue(m4)

        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2], [m3, procurement_order_3],
                             [m4, False]])
        test_increasing_line_qty(line, 110, 4, [[m1, 7], [m2, 40], [m3, 50]])
        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2], [m3, procurement_order_3]])
        test_increasing_line_qty(line, 210, 4, [[m1, 7], [m2, 40], [m3, 50]])
        test_procurement_id([[m1, procurement_order_1], [m2, procurement_order_2], [m3, procurement_order_3]])
        for move in [m1, m2, m3]:
            self.assertTrue(move.picking_id)
            self.assertTrue(move.picking_type_id)
        self.assertRaises(exceptions.MissingError, getattr, m4, 'name')
        picking = m1.picking_id
        self.assertTrue(m2 in picking.move_lines)
        self.assertTrue(m3 in picking.move_lines)

        self.env['procurement.order'].purchase_schedule(jobify=False)
        self.assertEqual(purchase_order_1.state, 'approved')

    def test_61_purchase_procurement_jit(self):
        """
        Testing procurement date no change
        """
        _, _, proc4 = self.create_and_run_proc_1_2_4()
        self.supplierinfo2.min_qty = 10
        purchase_order_1 = proc4.purchase_id
        _, line = self.check_purchase_order_1_2_4(purchase_order_1)
        self.assertEqual(proc4.date_planned, "3003-05-05 17:00:00")

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(purchase_order_1.state, 'approved')
        self.assertEqual(len(line.move_ids), 2)
        for move in line.move_ids:
            self.assertIn((move.product_uom_qty, move.state, move.procurement_id),
                          [(2, 'assigned', self.env['procurement.order']), (8, 'assigned', proc4)])

        picking = purchase_order_1.picking_ids[0]
        picking.do_prepare_partial()
        packop = self.env['stock.pack.operation'].search([('product_id', '=', self.product2.id),
                                                          ('picking_id', '=', picking.id)])
        packop.product_qty = 3
        picking.do_transfer()

        move2 = self.env['stock.move']
        for move in line.move_ids:
            if move.product_uom_qty == 2:
                move2 = move
            self.assertIn((move.product_uom_qty, move.state, move.procurement_id),
                          [(2, 'assigned', self.env['procurement.order']), (5, 'assigned', proc4), (3, 'done', proc4)])

        # self.assertEqual(m3.procurement_id, proc4)
        self.assertEqual(proc4.date_planned, "3003-05-05 17:00:00")

        move3 = self.env['stock.move'].browse(self.env['stock.move'].split(move2, 1))
        move3.action_done()

        move4 = self.env['stock.move']
        for move in line.move_ids:
            if move.product_uom_qty == 3:
                move4 = move
            self.assertIn((move.product_uom_qty, move.state, move.procurement_id),
                          [(1, 'assigned', self.env['procurement.order']),
                           (1, 'done', self.env['procurement.order']),
                           (5, 'assigned', proc4),
                           (3, 'done', proc4)])

        self.env['procurement.order'].purchase_schedule(jobify=False)

        line.product_qty = 11

        for move in line.move_ids:
            self.assertIn((move.product_uom_qty, move.state, move.procurement_id),
                          [(5, 'assigned', move4.procurement_id),
                           (2, 'assigned', self.env['procurement.order']),
                           (1, 'done', self.env['procurement.order']),
                           (3, 'done', move4.procurement_id)])

        line.product_qty = 9
        for move in line.move_ids:
            self.assertIn((move.product_uom_qty, move.state, move.procurement_id),
                          [(1, 'done', self.env['procurement.order']),
                           (5, 'assigned', move4.procurement_id),
                           (3, 'done', move4.procurement_id)])

    def test_62_purchase_procurement_jit(self):
        """
        Testing purchase no picking exception
        """
        proc1, proc2 = self.create_and_run_proc_1_2()
        purchase_order_1 = proc1.purchase_id
        line = self.check_purchase_order_1_2(purchase_order_1)

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(purchase_order_1.state, 'approved')

        line.product_qty = 30

        picking = purchase_order_1.picking_ids[0]
        picking.do_prepare_partial()
        packop = self.env['stock.pack.operation'].search([('picking_id', '=', picking.id)])
        packop.product_qty = 14
        picking.do_transfer()

        self.assertEqual(len(line.procurement_ids), 1)
        self.assertEqual(line.procurement_ids[0], proc1)
        self.assertEqual(proc1.state, 'done')

        self.env['procurement.order'].purchase_schedule(jobify=False)
        self.assertEqual(purchase_order_1.state, 'approved')
        line.product_qty = 58
        self.env['procurement.order'].purchase_schedule(jobify=False)
        self.assertEqual(purchase_order_1.state, 'approved')

    def test_63_purchase_procurement_jit(self):
        """
        Testing defective procurement
        """
        proc1, proc2 = self.create_and_run_proc_1_2()
        purchase_order_1 = proc1.purchase_id
        line = self.check_purchase_order_1_2(purchase_order_1)

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(purchase_order_1.state, 'approved')

        line.product_qty = 51

        m1 = self.env['stock.move']
        for move in line.move_ids:
            self.assertIn(move.product_uom_qty, [7, 40, 4])
            if move.product_qty == 7:
                m1 = move

        m1.product_uom_qty = 5
        self.env['procurement.order'].create({
            'name': 'Procurement order 1bis (Purchase Procurement JIT)',
            'product_id': self.product1.id,
            'product_qty': 2,
            'warehouse_id': self.warehouse.id,
            'location_id': self.location_a.id,
            'date_planned': '3003-05-04 15:00:00',
            'product_uom': self.ref('product.product_uom_unit'),
            'state': 'cancel',
            'purchase_line_id': line.id,
        })

        line.product_qty = 52
        self.assertEqual(len(line.move_ids), 3)
        for move in line.move_ids:
            self.assertIn(move.product_uom_qty, [5, 40, 7])

        line.product_qty = 47
        self.assertEqual(len(line.move_ids), 3)
        for move in line.move_ids:
            self.assertIn(move.product_uom_qty, [5, 40, 2])

        line.product_qty = 45
        self.assertEqual(len(line.move_ids), 2)
        for move in line.move_ids:
            self.assertIn(move.product_uom_qty, [5, 40])

    def test_65_purchase_procurement_jit(self):
        """
        Testing draft purchase order lines splits
        """
        procurement_order_1, procurement_order_2 = self.create_and_run_proc_1_2()
        purchase_order_1 = procurement_order_1.purchase_id
        line = self.check_purchase_order_1_2(purchase_order_1)

        purchase_order_1.signal_workflow('purchase_confirm')

        [move1, move2, move3] = [False] * 3

        for move in line.move_ids:
            if move.product_uom_qty == 1 and move.product_uom == self.unit:
                move1 = move
            elif move.product_uom_qty == 7 and move.product_uom == self.unit:
                move2 = move
            elif move.product_uom_qty == 40 and move.product_uom == self.unit:
                move3 = move
        self.assertTrue(move1 and move2 and move3)

        move1.product_uom_qty = 0.5
        move1.product_uom = self.uom_couple
        move2.product_uom_qty = 3.5
        move2.product_uom = self.uom_couple
        move3.product_uom_qty = 10
        move3.product_uom = self.uom_four

        split = self.env['split.line'].create({'line_id': line.id, 'qty': 20})
        split.do_split()
        self.assertEqual(len(purchase_order_1.order_line), 2)
        self.assertIn(line, purchase_order_1.order_line)
        line2 = [l for l in purchase_order_1.order_line if l != line][0]
        self.assertEqual(line2.father_line_id, line)
        self.assertEqual(line.children_number, 1)
        self.assertEqual(line2.line_no, '010 - 1')
        self.assertEqual(line2.product_qty, 28)
        self.assertEqual(sum([m.product_uom_qty for m in line2.move_ids if m.state != 'cancel']), 28)

        self.assertEqual(len(line.move_ids), 2)
        [m1, m2] = [False, False]
        for move in line.move_ids:
            if move.procurement_id:
                m1 = move
            else:
                m2 = move
        self.assertTrue(m1 and m2)
        self.assertEqual(m1.product_uom_qty, 3.5)
        self.assertEqual(m1.product_uom, self.uom_couple)
        self.assertEqual(m2.product_uom_qty, 13)
        self.assertEqual(m2.product_uom, self.unit)
        self.assertEqual(m1.procurement_id, procurement_order_1)

        split = self.env['split.line'].create({'line_id': line2.id, 'qty': 10})
        split.do_split()
        self.assertEqual(len(purchase_order_1.order_line), 3)
        self.assertIn(line, purchase_order_1.order_line)
        self.assertIn(line2, purchase_order_1.order_line)
        line3 = [l for l in purchase_order_1.order_line if l not in [line, line2]][0]
        self.assertEqual(line3.father_line_id, line)
        self.assertEqual(line.children_number, 2)
        self.assertEqual(line3.line_no, '010 - 2')
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
        self.assertEqual(line1.line_no, '010 - 3')
        self.assertEqual(line1.product_qty, 15)

        purchase_order_1.signal_workflow('purchase_confirm')

        self.assertEqual(len(line.move_ids), 1)
        m1 = line.move_ids[0]
        self.assertTrue(m1)
        self.assertFalse(m1.procurement_id)
        self.assertEqual(len(line1.move_ids), 1)
        self.assertEqual(line1.move_ids[0].product_qty, 15)
        self.assertEqual(len(line2.move_ids), 1)
        self.assertEqual(line2.move_ids[0].product_qty, 10)
        self.assertEqual(len(line3.move_ids), 1)
        self.assertEqual(line3.move_ids[0].product_qty, 18)

    def test_70_purchase_procurement_jit(self):
        """
        Testing confirmed purchase order lines splits
        """
        procurement_order_1, procurement_order_2 = self.create_and_run_proc_1_2()
        purchase_order_1 = procurement_order_1.purchase_id
        line = self.check_purchase_order_1_2(purchase_order_1)

        purchase_order_1.signal_workflow('purchase_confirm')

        self.assertEqual(len(line.move_ids), 3)
        for m in line.move_ids:
            self.assertIn(m.product_uom_qty, [1, 7, 40])

        split = self.env['split.line'].create({'line_id': line.id, 'qty': 20})
        split.do_split()
        self.assertEqual(len(purchase_order_1.order_line), 2)
        self.assertIn(line, purchase_order_1.order_line)
        line2 = [l for l in purchase_order_1.order_line if l != line][0]
        self.assertEqual(line2.father_line_id, line)
        self.assertEqual(line.children_number, 1)
        self.assertEqual(line2.line_no, '010 - 1')
        self.assertEqual(line2.product_qty, 28)
        self.assertEqual(line2.remaining_qty, 28)
        self.assertEqual(len(line.move_ids), 2)
        for m in line.move_ids:
            self.assertIn(m.product_uom_qty, [7, 13])
        self.assertEqual(line2.move_ids[0].product_uom_qty, 28)

        split = self.env['split.line'].create({'line_id': line2.id, 'qty': 10})
        split.do_split()
        self.assertEqual(len(purchase_order_1.order_line), 3)
        self.assertIn(line, purchase_order_1.order_line)
        self.assertIn(line2, purchase_order_1.order_line)
        line3 = [l for l in purchase_order_1.order_line if l not in [line, line2]][0]
        self.assertEqual(line3.father_line_id, line)
        self.assertEqual(line.children_number, 2)
        self.assertEqual(line3.line_no, '010 - 2')
        self.assertEqual(line3.product_qty, 18)
        self.assertEqual(line3.remaining_qty, 18)
        self.assertEqual(len(line.move_ids), 2)
        for m in line.move_ids:
            self.assertIn(m.product_uom_qty, [7, 13])
        self.assertEqual(len(line2.move_ids), 1)
        self.assertEqual(line2.move_ids[0].product_uom_qty, 10)

        self.assertEqual(len(line3.move_ids), 1)
        self.assertEqual(line3.move_ids[0].product_uom_qty, 18)

        split = self.env['split.line'].create({'line_id': line.id, 'qty': 5})
        split.do_split()
        self.assertEqual(len(purchase_order_1.order_line), 4)
        self.assertIn(line, purchase_order_1.order_line)
        self.assertIn(line2, purchase_order_1.order_line)
        self.assertIn(line3, purchase_order_1.order_line)
        line1 = [l for l in purchase_order_1.order_line if l not in [line, line2, line3]][0]
        self.assertEqual(line1.father_line_id, line)
        self.assertEqual(line.children_number, 3)
        self.assertEqual(line1.line_no, '010 - 3')
        self.assertEqual(line1.product_qty, 15)
        self.assertEqual(line1.remaining_qty, 15)
        self.assertEqual(len(line.move_ids), 1)
        self.assertEqual(line.move_ids[0].product_uom_qty, 5)
        self.assertFalse(line.move_ids[0].procurement_id)
        self.assertEqual(len(line2.move_ids), 1)
        self.assertEqual(line2.move_ids[0].product_uom_qty, 10)
        self.assertFalse(line2.move_ids[0].procurement_id)
        self.assertEqual(len(line3.move_ids), 1)
        self.assertEqual(line3.move_ids[0].product_uom_qty, 18)
        self.assertFalse(line3.move_ids[0].procurement_id)
        self.assertEqual(len(line1.move_ids), 1)
        self.assertEqual(line1.move_ids[0].product_uom_qty, 15)
        self.assertFalse(line1.move_ids[0].procurement_id)

    def test_80_purchase_jit_cancelling_proc_and_then_purchase_order(self):
        self.create_and_run_proc_1_2()
        procurement_order_1, procurement_order_2 = self.create_and_run_proc_1_2()
        order1 = procurement_order_1.purchase_id
        self.assertTrue(order1)
        purchase_line1 = procurement_order_1.purchase_line_id
        self.assertTrue(purchase_line1)
        self.assertEqual(procurement_order_1.state, 'running')

        order1.signal_workflow('purchase_confirm')
        procurement_order_1.cancel()
        self.assertEqual(procurement_order_1.state, 'cancel')
        order1.action_cancel()
        self.assertEqual(procurement_order_1.state, 'cancel')

    def test_81_purchase_jit_cancelling_proc_and_then_unlink_purchase_line(self):
        self.create_and_run_proc_1_2()
        procurement_order_1, procurement_order_2 = self.create_and_run_proc_1_2()
        order1 = procurement_order_1.purchase_id
        self.assertTrue(order1)
        purchase_line1 = procurement_order_1.purchase_line_id
        self.assertTrue(purchase_line1)
        self.assertEqual(procurement_order_1.state, 'running')

        procurement_order_1.cancel()
        self.assertEqual(procurement_order_1.state, 'cancel')
        purchase_line1.unlink()
        self.assertEqual(procurement_order_1.state, 'cancel')

    def test_90_reset_exception_to_confirmed(self):
        proc1, proc2 = self.create_and_run_proc_1_2()
        purchase_order_1 = proc1.purchase_id
        line = self.check_purchase_order_1_2(purchase_order_1)
        self.assertEqual(line.product_qty, 48)

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(purchase_order_1.state, 'approved')
        self.assertTrue(line.move_ids)
        picking = line.move_ids[0].picking_id
        self.assertTrue(picking)
        for move in line.move_ids:
            self.assertEqual(move.picking_id, picking)

        # We create a backorder
        picking.do_prepare_partial()
        wizard_id = picking.do_enter_transfer_details()['res_id']
        wizard = self.env['stock.transfer_details'].browse(wizard_id)
        self.assertEqual(len(wizard.item_ids), 1)
        self.assertEqual(wizard.item_ids.quantity, 48)
        wizard.item_ids.quantity = 20
        wizard.do_detailed_transfer()

        # We cancel the backorder to create a picking exception
        backorder = self.env['stock.picking'].search([('backorder_id', '=', picking.id)])
        self.assertEqual(len(backorder), 1)
        self.assertNotEqual(backorder.state, 'done')
        backorder.action_cancel()
        self.assertEqual(purchase_order_1.state, 'except_picking')

        # We test function reset_to_confirmed
        self.assertFalse(line.move_ids.filtered(lambda sm: sm.state not in ['draft', 'done', 'cancel']))
        purchase_order_1.reset_to_confirmed()
        self.assertEqual(purchase_order_1.state, 'approved')
        new_move = line.move_ids.filtered(lambda sm: sm.state not in ['draft', 'done', 'cancel'])
        self.assertEqual(len(new_move), 1)
        self.assertEqual(new_move.product_qty, 28)
