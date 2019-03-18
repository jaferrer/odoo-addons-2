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
from openerp.tools.misc import frozendict
from openerp.tests import common



class TestPurchaseProcurementJIT(common.TransactionCase):

    def setUp(self):
        super(TestPurchaseProcurementJIT, self).setUp()
        self.env.context = frozendict(dict(self.env.context, check_product_qty=False))
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
        self.cron_stock_scheduler = self.browse_ref('stock_procurement_just_in_time.job_update_scheduler_controller')
        self.cron_stock_scheduler.active = False
        self.env['stock.scheduler.controller'].search([]).write({'done': True})

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

    def test_10_cancel_procs_in_draft_order(self):
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
        purchase_order_1 = new_proc_1.purchase_id
        self.assertTrue(purchase_order_1)
        self.assertEqual(len(purchase_order_1.order_line), 1)
        self.assertEqual(purchase_order_1.order_line[0].product_qty, 36)
        self.assertEqual(purchase_order_1.order_line[0].product_id, self.product1)

        self.assertEqual(procurement_order_1.state, 'cancel')
        self.assertEqual(procurement_order_2.state, 'cancel')
        self.assertEqual(procurement_order_4.state, 'cancel')

    def test_15_proc_exception_when_no_supplier(self):
        proc = self.create_procurement_order_5()
        proc.run()
        self.assertEqual(proc.state, 'exception')
        self.assertEqual(len(proc.message_ids), 1)
        proc.cancel()
        self.env.invalidate_all()
        proc.unlink_useless_messages()
        self.assertEqual(len(proc.message_ids), 0)

    def test_20_cancel_proc_in_confirmed_order(self):
        procurement_order_1, procurement_order_2, procurement_order_4 = self.create_and_run_proc_1_2_4()
        purchase_order_1 = procurement_order_1.purchase_id
        line1, line2 = self.check_purchase_order_1_2_4(purchase_order_1)

        # Let's confirm our purchase order
        def check_purchase_order_with_procs():
            self.assertEqual(purchase_order_1.state, 'approved')
            move1 = line1.move_ids
            self.assertEqual(len(move1), 1)
            self.assertEqual(move1.product_uom_qty, 48)
            self.assertEqual(move1.state, 'assigned')
            self.assertFalse(move1.procurement_id)

            self.assertEqual(line2.product_qty, 10)
            self.assertEqual(line2.procurement_ids, procurement_order_4)
            move2 = line2.move_ids
            self.assertEqual(len(move2), 1)
            self.assertEqual(move2.product_uom_qty, 10)
            self.assertEqual(move2.state, 'assigned')
            self.assertFalse(move2.procurement_id)
            self.assertFalse(move2.move_dest_id)

            self.assertEqual(len(line1.order_id.picking_ids), 1)
            picking_recpt = line1.order_id.picking_ids
            self.assertEqual(len(picking_recpt.move_lines), 2)
            self.assertIn([48, self.product1, self.env['procurement.order'], 'assigned'],
                          [[x.product_uom_qty, x.product_id, x.procurement_id, x.state] for x in
                           picking_recpt.move_lines])
            self.assertIn([10, self.product2, self.env['procurement.order'], 'assigned'],
                          [[x.product_uom_qty, x.product_id, x.procurement_id, x.state] for x in
                           picking_recpt.move_lines])

        def check_purchase_order_without_procs():
            self.assertEqual(purchase_order_1.state, 'approved')
            move1 = line1.move_ids
            self.assertEqual(len(move1), 1)
            self.assertEqual(move1.product_uom_qty, 48)
            self.assertEqual(move1.state, 'assigned')
            self.assertFalse(move1.procurement_id)

            move2 = line2.move_ids
            self.assertEqual(len(move2), 1)
            self.assertEqual(move2.product_uom_qty, 10)
            self.assertEqual(move2.state, 'assigned')
            self.assertFalse(move2.procurement_id)
            self.assertFalse(move2.move_dest_id)

            self.assertEqual(len(line1.order_id.picking_ids), 1)
            picking_recpt = line1.order_id.picking_ids
            self.assertEqual(len(picking_recpt.move_lines), 2)
            self.assertIn([48, self.product1, self.env['procurement.order'], 'assigned'],
                          [[x.product_uom_qty, x.product_id, x.procurement_id, x.state] for x in
                           picking_recpt.move_lines])
            self.assertIn([10, self.product2, self.env['procurement.order'], 'assigned'],
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

    def test_30_set_line_qty_to_zero(self):
        procurement_order_1, procurement_order_2, procurement_order_3 = self.create_and_run_proc_1_2_3()
        purchase_order_1 = procurement_order_1.purchase_id
        line = self.check_purchase_order_1_2_3(purchase_order_1)

        line.write({'product_qty': 0})

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(len(purchase_order_1.order_line), 1)
        self.assertIn(line, purchase_order_1.order_line)
        self.assertEqual(len(line.move_ids), 0)

    def test_35_draft_order_line_removed(self):
        procurement_order_1, procurement_order_2, procurement_order_4 = self.create_and_run_proc_1_2_4()
        purchase_order_1 = procurement_order_1.purchase_id
        line1, line2 = self.check_purchase_order_1_2_4(purchase_order_1)

        line2.unlink()

        self.assertEqual(len(purchase_order_1.order_line), 1)
        self.assertIn(line1, purchase_order_1.order_line)
        self.assertEqual(procurement_order_4.state, 'buy_to_run')
        self.assertEqual(len(procurement_order_4.message_ids), 1)
        procurement_order_4.cancel()
        self.env.invalidate_all()
        procurement_order_4.unlink_useless_messages()
        self.assertEqual(len(procurement_order_4.message_ids), 0)

    def test_40_manual_purchase_order_manipulation(self):
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
        move1 = line.move_ids
        self.assertEqual(len(move1), 1)
        self.assertEqual(move1.product_uom_qty, 10)
        line.product_qty = 11
        self.assertEqual(order.state, 'approved')
        self.assertEqual(len(line.move_ids), 2)
        self.assertIn(move1, line.move_ids)
        move2 = line.move_ids.filtered(lambda move: move != move1)
        self.assertEqual(move1.product_uom_qty, 10)
        self.assertEqual(move2.product_uom_qty, 1)
        line.product_qty = 9
        self.assertEqual(order.state, 'approved')
        self.assertEqual(line.move_ids.filtered(lambda move: move.state != 'cancel')[0].product_uom_qty, 9)

        picking = order.picking_ids[0]
        picking.do_prepare_partial()
        packop = self.env['stock.pack.operation'].search([('product_id', '=', self.product1.id),
                                                          ('picking_id', '=', picking.id)])
        packop.product_qty = 5
        picking.do_transfer()

        self.assertEqual(order.state, 'approved')
        self.assertEqual(len(line.move_ids.filtered(lambda move: move.state != 'cancel')), 2)
        self.assertIn((4, 'assigned'), [(m.product_uom_qty, m.state) for m in line.move_ids.filtered(lambda move: move.state != 'cancel')])
        self.assertIn((5, 'done'), [(m.product_uom_qty, m.state) for m in line.move_ids.filtered(lambda move: move.state != 'cancel')])

        line.product_qty = 5
        self.assertEqual(len(line.move_ids.filtered(lambda move: move.state != 'cancel')), 1)
        self.assertEqual(line.move_ids.filtered(lambda move: move.state != 'cancel')[0].product_uom_qty, 5)

    def test_45_increasing_qty_draft_purchase_order_line(self):
        procurement_order_1, procurement_order_2, procurement_order_3 = self.create_and_run_proc_1_2_3()
        purchase_order_1 = procurement_order_1.purchase_id
        line = self.check_purchase_order_1_2_3(purchase_order_1)

        line.write({'product_qty': 110})

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(len(purchase_order_1.order_line), 1)
        self.assertIn(line, purchase_order_1.order_line)
        move = line.move_ids
        self.assertEqual(len(move), 1)
        self.assertFalse(move.procurement_id)
        self.assertEqual(move.product_uom_qty, 110)
        self.assertEqual(move.state, 'assigned')

    def test_50_decrease_qty_of_confirmed_line(self):
        def test_decreasing_line_qty(line_tested, new_qty, list_quantities):
            line_tested.write({'product_qty': new_qty})
            self.assertEqual(len(line_tested.move_ids.filtered(lambda move: move.state != 'cancel')), len(list_quantities))
            for item in list_quantities:
                self.assertIn(item, [x.product_qty for x in line_tested.move_ids.filtered(lambda move: move.state != 'cancel')])

        procurement_order_1, procurement_order_2, procurement_order_3 = self.create_and_run_proc_1_2_3()
        purchase_order_1 = procurement_order_1.purchase_id
        line = self.check_purchase_order_1_2_3(purchase_order_1)

        purchase_order_1.signal_workflow('purchase_confirm')

        move = line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.product_qty, 108)

        test_decreasing_line_qty(line, 107, [107])
        test_decreasing_line_qty(line, 100, [100])
        test_decreasing_line_qty(line, 1, [1])
        line.product_qty = 0
        self.assertFalse(line.move_ids.filtered(lambda move: move.state != 'cancel'))
        self.assertEqual(purchase_order_1.state, 'approved')

    def test_55_cancelling_confirmed_purchase_order(self):
        procurement_order_1, procurement_order_2, procurement_order_4 = self.create_and_run_proc_1_2_4()
        purchase_order_1 = procurement_order_1.purchase_id
        line1, line2 = self.check_purchase_order_1_2_4(purchase_order_1)

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(purchase_order_1.state, 'approved')
        self.assertEqual(line1.state, 'confirmed')
        self.assertEqual(line2.state, 'confirmed')

        move2 = line2.move_ids
        self.assertEqual(len(move2), 1)
        self.assertEqual(move2.product_uom_qty, 10)
        self.assertEqual(move2.state, 'assigned')
        self.assertFalse(move2.procurement_id)
        self.assertFalse(move2.move_dest_id)

        purchase_order_1.action_cancel()

        self.assertEqual(procurement_order_1.state, 'buy_to_run')
        self.assertEqual(procurement_order_2.state, 'buy_to_run')
        self.assertEqual(procurement_order_4.state, 'buy_to_run')
        self.assertEqual(move2.state, 'cancel')

    def test_57_decrease_line_qty_with_done_moves(self):
        def test_decreasing_line_qty(line_tested, new_qty, list_quantities):
            line_tested.write({'product_qty': new_qty})
            self.assertEqual(len(line_tested.move_ids.filtered(lambda move: move.state not in ['done', 'cancel'])),
                             len(list_quantities))
            for item in list_quantities:
                self.assertIn(item,[x.product_qty for x in
                                    line_tested.move_ids.filtered(lambda move: move.state not in ['done', 'cancel'])])

        procurement_order_1, procurement_order_2, procurement_order_3 = self.create_and_run_proc_1_2_3()
        purchase_order_1 = procurement_order_1.purchase_id
        line = self.check_purchase_order_1_2_3(purchase_order_1)

        purchase_order_1.signal_workflow('purchase_confirm')

        move = line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.product_uom_qty, 108)

        picking = move.picking_id
        self.assertTrue(move)
        picking.do_prepare_partial()
        packop = self.env['stock.pack.operation'].search([('product_id', '=', self.product1.id),
                                                          ('picking_id', '=', picking.id)])
        packop.product_qty = 18
        picking.do_transfer()
        self.assertEqual(move.state, 'done')
        self.assertEqual(move.product_qty, 18)

        test_decreasing_line_qty(line, 106, [88])
        test_decreasing_line_qty(line, 50, [32])
        test_decreasing_line_qty(line, 18, [])
        with self.assertRaises(exceptions.except_orm):
            test_decreasing_line_qty(line, 17, [])

        # Let's run the scheduler to check that nothing changes
        self.env['procurement.order'].purchase_schedule(jobify=False)
        end_move = line.move_ids.filtered(lambda move: move.state != 'cancel')
        self.assertEqual(len(end_move), 1)
        self.assertEqual(end_move, move)

        # Let's increase/decrease again to check
        self.assertEqual(line.order_id.state, 'approved')
        test_decreasing_line_qty(line, 19, [1])
        test_decreasing_line_qty(line, 18, [])

    def test_58_purchase_procurement_jit(self):
        """
        Deleting a draft purchase order
        """
        procurement_order_1, procurement_order_2, procurement_order_4 = self.create_and_run_proc_1_2_4()
        purchase_order_1 = procurement_order_1.purchase_id
        self.check_purchase_order_1_2_4(purchase_order_1)

        self.assertEqual(purchase_order_1.state, 'draft')
        self.assertEqual(procurement_order_1.state, 'running')
        self.assertEqual(procurement_order_2.state, 'running')
        self.assertEqual(procurement_order_4.state, 'running')
        purchase_order_1.unlink()

        self.assertEqual(procurement_order_1.state, 'buy_to_run')
        self.assertEqual(procurement_order_2.state, 'buy_to_run')
        self.assertEqual(procurement_order_4.state, 'buy_to_run')

    def test_60_purchase_no_picking_exception(self):
        proc1, proc2 = self.create_and_run_proc_1_2()
        purchase_order_1 = proc1.purchase_id
        line = self.check_purchase_order_1_2(purchase_order_1)

        purchase_order_1.signal_workflow('purchase_confirm')
        self.assertEqual(purchase_order_1.state, 'approved')
        self.assertEqual(line.product_qty, 48)

        line.product_qty = 30

        picking = purchase_order_1.picking_ids[0]
        picking.do_prepare_partial()
        packop = self.env['stock.pack.operation'].search([('picking_id', '=', picking.id)])
        packop.product_qty = 13
        picking.do_transfer()

        # Procs were splitted and 14 units were set to done
        self.assertEqual(len(line.procurement_ids), 3)
        self.assertIn(proc1, line.procurement_ids)
        self.assertIn(proc2, line.procurement_ids)
        proc3 = line.procurement_ids.filtered(lambda proc: proc not in [proc1, proc2])
        self.assertEqual(proc1.product_qty, 7)
        self.assertEqual(proc1.state, 'done')
        self.assertEqual(proc2.product_qty, 6)
        self.assertEqual(proc2.state, 'done')
        self.assertEqual(proc3.product_qty, 34)
        self.assertEqual(proc3.state, 'running')

        self.env['procurement.order'].purchase_schedule(jobify=False)
        self.assertEqual(purchase_order_1.state, 'approved')
        line.product_qty = 58
        self.env['procurement.order'].purchase_schedule(jobify=False)
        self.assertEqual(purchase_order_1.state, 'approved')

    def test_65_draft_order_line_split(self):
        """
        Testing draft purchase order lines splits
        """
        procurement_order_1, procurement_order_2 = self.create_and_run_proc_1_2()
        purchase_order_1 = procurement_order_1.purchase_id
        line = self.check_purchase_order_1_2(purchase_order_1)

        purchase_order_1.signal_workflow('purchase_confirm')

        move = line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.product_uom_qty, 48)

        move.product_uom_qty = 12
        move.product_uom = self.uom_four

        split = self.env['split.line'].create({'line_id': line.id, 'qty': 20})
        split.do_split()
        self.assertEqual(len(purchase_order_1.order_line), 2)
        self.assertIn(line, purchase_order_1.order_line)
        line2 = [l for l in purchase_order_1.order_line if l != line][0]
        self.assertEqual(line2.father_line_id, line)
        self.assertEqual(line.children_number, 1)
        self.assertEqual(line2.line_no, '010 - 1')
        self.assertEqual(line2.product_qty, 28)
        self.assertEqual(sum([m.product_uom_qty for m in line2.move_ids.filtered(lambda move: move.state != 'cancel')]), 28)

        move = line.move_ids.filtered(lambda move: move.state != 'cancel')
        self.assertEqual(len(move), 1)
        self.assertEqual(move.product_uom_qty, 20)
        self.assertEqual(move.product_uom, self.unit)
        self.assertFalse(move.procurement_id)

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

        self.assertEqual(len(line.move_ids.filtered(lambda move: move.state != 'cancel')), 1)
        m1 = line.move_ids.filtered(lambda move: move.state != 'cancel')
        self.assertTrue(m1)
        self.assertFalse(m1.procurement_id)
        self.assertEqual(len(line1.move_ids.filtered(lambda move: move.state != 'cancel')), 1)
        self.assertEqual(line1.move_ids.filtered(lambda move: move.state != 'cancel')[0].product_qty, 15)
        self.assertEqual(len(line2.move_ids.filtered(lambda move: move.state != 'cancel')), 1)
        self.assertEqual(line2.move_ids.filtered(lambda move: move.state != 'cancel')[0].product_qty, 10)
        self.assertEqual(len(line3.move_ids.filtered(lambda move: move.state != 'cancel')), 1)
        self.assertEqual(line3.move_ids.filtered(lambda move: move.state != 'cancel')[0].product_qty, 18)

    def test_70_confirmed_lines_split(self):
        procurement_order_1, procurement_order_2 = self.create_and_run_proc_1_2()
        purchase_order_1 = procurement_order_1.purchase_id
        line = self.check_purchase_order_1_2(purchase_order_1)

        purchase_order_1.signal_workflow('purchase_confirm')

        move = line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.product_qty, 48)

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
        self.assertEqual(len(line.move_ids.filtered(lambda move: move.state != 'cancel')), 1)
        move = line.move_ids.filtered(lambda move: move.state != 'cancel')
        self.assertEqual(len(move), 1)
        self.assertEqual(move.product_uom_qty, 20)
        self.assertEqual(line2.move_ids.filtered(lambda move: move.state != 'cancel')[0].product_uom_qty, 28)

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
        self.assertEqual(len(line.move_ids.filtered(lambda move: move.state != 'cancel')), 1)
        move = line.move_ids.filtered(lambda move: move.state != 'cancel')
        self.assertEqual(len(move), 1)
        self.assertEqual(move.product_uom_qty, 20)
        self.assertEqual(len(line2.move_ids.filtered(lambda move: move.state != 'cancel')), 1)
        self.assertEqual(line2.move_ids.filtered(lambda move: move.state != 'cancel')[0].product_uom_qty, 10)

        self.assertEqual(len(line3.move_ids.filtered(lambda move: move.state != 'cancel')), 1)
        self.assertEqual(line3.move_ids.filtered(lambda move: move.state != 'cancel')[0].product_uom_qty, 18)

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
        self.assertEqual(len(line.move_ids.filtered(lambda move: move.state != 'cancel')), 1)
        self.assertEqual(line.move_ids.filtered(lambda move: move.state != 'cancel')[0].product_uom_qty, 5)
        self.assertFalse(line.move_ids.filtered(lambda move: move.state != 'cancel')[0].procurement_id)
        self.assertEqual(len(line2.move_ids.filtered(lambda move: move.state != 'cancel')), 1)
        self.assertEqual(line2.move_ids.filtered(lambda move: move.state != 'cancel')[0].product_uom_qty, 10)
        self.assertFalse(line2.move_ids.filtered(lambda move: move.state != 'cancel')[0].procurement_id)
        self.assertEqual(len(line3.move_ids.filtered(lambda move: move.state != 'cancel')), 1)
        self.assertEqual(line3.move_ids.filtered(lambda move: move.state != 'cancel')[0].product_uom_qty, 18)
        self.assertFalse(line3.move_ids.filtered(lambda move: move.state != 'cancel')[0].procurement_id)
        self.assertEqual(len(line1.move_ids.filtered(lambda move: move.state != 'cancel')), 1)
        self.assertEqual(line1.move_ids.filtered(lambda move: move.state != 'cancel')[0].product_uom_qty, 15)
        self.assertFalse(line1.move_ids.filtered(lambda move: move.state != 'cancel')[0].procurement_id)

    def test_75_purchase_jit_cancelling_proc_and_then_purchase_order(self):
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

    def test_80_purchase_jit_cancelling_proc_and_then_unlink_purchase_line(self):
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

    def test_85_reset_exception_to_confirmed(self):
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
