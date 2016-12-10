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

from datetime import datetime as dt

from openerp import fields
from openerp.tests import common


class TestPurchaseScheduler(common.TransactionCase):
    def setUp(self):
        super(TestPurchaseScheduler, self).setUp()
        self.company = self.browse_ref('base.main_company')
        self.company.write({'po_lead': 5, 'security_lead': 4})
        self.supplier = self.browse_ref('purchase_procurement_just_in_time.supplier1')
        self.product1 = self.browse_ref('purchase_procurement_just_in_time.product1')
        self.product2 = self.browse_ref('purchase_procurement_just_in_time.product2')
        self.product_uom = self.browse_ref('product.product_uom_unit')
        self.location_a = self.browse_ref('purchase_procurement_just_in_time.stock_location_a')
        self.location_b = self.browse_ref('purchase_procurement_just_in_time.stock_location_b')
        self.procurement_rule_a_to_b = self.browse_ref('purchase_procurement_just_in_time.procurement_rule_a_to_b')
        self.procurement_rule_a_buy = self.browse_ref('purchase_procurement_just_in_time.procurement_rule_a_buy')
        self.warehouse = self.browse_ref('stock.warehouse0')
        self.frame_week = self.browse_ref('purchase_procurement_just_in_time.week')
        self.unit = self.browse_ref('product.product_uom_unit')
        self.loc_supplier = self.browse_ref('stock.stock_location_suppliers')
        self.picking_type_in = self.browse_ref('stock.picking_type_in')

        self.prepare_procurements()

        configuration_wizard = self.env['purchase.config.settings'].create({'delta_begin_grouping_period': False,
                                                                            'ignore_past_procurements': False})
        configuration_wizard.execute()

    # Tests are made in 3003, so that all the data remain in the future. Dates of 3003 are the same as dates of 2016.

    def prepare_proc_1(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 1 (Purchase Procurement JIT)',
            'product_id': self.product1.id,
            'product_qty': 34,
            'warehouse_id': self.warehouse.id,
            'location_id': self.location_a.id,
            'date_planned': '3003-09-04 15:00:00',
            'product_uom': self.product_uom.id,
        })

    def prepare_proc_2(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 2 (Purchase Procurement JIT)',
            'product_id': self.product1.id,
            'product_qty': 2,
            'warehouse_id': self.warehouse.id,
            'location_id': self.location_a.id,
            'date_planned': '3003-09-12 15:00:00',
            'product_uom': self.product_uom.id,
        })

    def prepare_proc_3(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 3 (Purchase Procurement JIT)',
            'product_id': self.product1.id,
            'product_qty': 33,
            'warehouse_id': self.warehouse.id,
            'location_id': self.location_a.id,
            'date_planned': '3003-09-22 15:00:00',
            'product_uom': self.product_uom.id,
        })

    def prepare_proc_4(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 4 (Purchase Procurement JIT)',
            'product_id': self.product1.id,
            'product_qty': 4,
            'warehouse_id': self.warehouse.id,
            'location_id': self.location_b.id,
            'date_planned': '3003-09-16 15:00:00',
            'product_uom': self.product_uom.id,
        })

    def prepare_proc_6(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 6(Purchase Procurement JIT)',
            'product_id': self.product2.id,
            'product_qty': 34,
            'warehouse_id': self.warehouse.id,
            'location_id': self.location_a.id,
            'date_planned': '3003-09-11 15:00:00',
            'product_uom': self.product_uom.id,
        })

    def prepare_procurements(self):
        self.proc1 = self.prepare_proc_1()
        self.proc2 = self.prepare_proc_2()
        self.proc3 = self.prepare_proc_3()
        self.proc4 = self.prepare_proc_4()
        self.proc6 = self.prepare_proc_6()
        self.proc1.run()
        self.assertEqual(self.proc1.state, 'buy_to_run')
        self.proc2.run()
        self.assertEqual(self.proc2.state, 'buy_to_run')
        self.proc3.run()
        self.assertEqual(self.proc3.state, 'buy_to_run')
        self.proc4.run()
        self.assertEqual(self.proc4.state, "running")
        self.assertEqual(len(self.proc4.move_ids), 1)
        self.proc5 = self.env['procurement.order'].search([('move_dest_id', '=', self.proc4.move_ids[0].id)])
        self.assertEqual(len(self.proc5), 1)
        self.assertEqual(self.proc5.date_planned[:10], '3003-09-14')
        self.proc5.run()
        self.assertEqual(self.proc5.state, 'buy_to_run')
        self.proc6.run()
        self.assertEqual(self.proc6.state, 'buy_to_run')

    def test_10_schedule_and_reschedule_from_scratch(self):
        """Test of purchase order creation from scratch when there are none at the beginning."""
        self.env['procurement.order'].purchase_schedule(compute_all_products=False, compute_supplier_ids=self.supplier,
                                                        jobify=False)
        purchase1 = self.proc1.purchase_id
        purchase2 = self.proc2.purchase_id
        purchase3 = self.proc3.purchase_id
        purchase5 = self.proc5.purchase_id
        purchase6 = self.proc6.purchase_id

        self.assertTrue(purchase1)
        self.assertTrue(purchase2)
        self.assertTrue(purchase3)
        self.assertTrue(purchase5)
        self.assertTrue(purchase6)

        self.assertEqual(purchase2, purchase1)
        self.assertEqual(purchase6, purchase1)
        self.assertNotEqual(purchase1, purchase5)
        self.assertNotEqual(purchase1, purchase3)
        self.assertNotEqual(purchase3, purchase5)

        self.assertEqual(purchase1.date_order[:10], '3003-08-22')
        self.assertEqual(purchase3.date_order[:10], '3003-09-12')
        self.assertEqual(purchase5.date_order[:10], '3003-09-05')

        # Let's change a date and reschedule
        self.proc1.date_planned = '3003-09-23 12:00:00'
        self.env['procurement.order'].purchase_schedule(compute_all_products=False, compute_supplier_ids=self.supplier,
                                                        jobify=False)

        purchase1 = self.proc1.purchase_id
        purchase2 = self.proc2.purchase_id
        purchase5 = self.proc5.purchase_id
        purchase3 = self.proc3.purchase_id

        self.assertTrue(purchase1)
        self.assertTrue(purchase2)
        self.assertTrue(purchase3)
        self.assertTrue(purchase5)

        self.assertNotEqual(purchase2, purchase1)
        self.assertNotEqual(purchase5, purchase1)
        self.assertEqual(purchase3, purchase1)
        self.assertNotEqual(purchase3, purchase5)

        self.assertEqual(purchase1.date_order, '3003-09-12 00:00:00')
        self.assertEqual(purchase1.date_order_max, '3003-09-18 23:59:59')
        self.assertEqual(purchase5.date_order, '3003-08-29 00:00:00')
        self.assertEqual(purchase5.date_order_max, '3003-09-04 23:59:59')

    def test_20_schedule_a_limited_number_of_orders(self):
        """Test of purchase order creation from scratch when nb_max_draft_orders is defined for the suplier."""
        self.supplier.nb_max_draft_orders = 2
        self.env['procurement.order'].purchase_schedule(compute_all_products=False, compute_product_ids=self.product1,
                                                        jobify=False)
        purchase1 = self.proc1.purchase_id
        purchase2 = self.proc2.purchase_id
        purchase3 = self.proc3.purchase_id
        purchase5 = self.proc5.purchase_id

        self.assertTrue(purchase1)
        self.assertTrue(purchase2)
        self.assertFalse(purchase3)
        self.assertTrue(purchase5)

        self.assertEqual(purchase2, purchase1)
        self.assertNotEqual(purchase1, purchase5)

        self.assertEqual(purchase1.date_order[:10], '3003-08-22')
        self.assertEqual(purchase5.date_order[:10], '3003-09-05')

    def test_30_schedule_ignore_past_procurements(self):
        """Test of scheduling past procurements with 'ignore past procurements' activated"""

        configuration_wizard = self.env['purchase.config.settings'].create({'ignore_past_procurements': True})
        configuration_wizard.execute()

        past_proc = self.env['procurement.order'].create({
            'name': 'Procurement order 1 (Purchase Procurement JIT)',
            'product_id': self.product1.id,
            'product_qty': 34,
            'warehouse_id': self.warehouse.id,
            'location_id': self.location_a.id,
            'date_planned': '2016-09-04 15:00:00',
            'product_uom': self.product_uom.id,
        })

        past_proc.run()
        self.assertEqual(past_proc.state, 'buy_to_run')

        self.env['procurement.order'].purchase_schedule(compute_all_products=False, compute_product_ids=self.product1,
                                                        compute_supplier_ids=self.supplier, jobify=False)
        purchase1 = self.proc1.purchase_id
        purchase2 = self.proc2.purchase_id
        purchase3 = self.proc3.purchase_id
        purchase5 = self.proc5.purchase_id

        self.assertTrue(purchase1)
        self.assertTrue(purchase2)
        self.assertTrue(purchase3)
        self.assertTrue(purchase5)

        self.assertEqual(purchase2, purchase1)
        self.assertNotEqual(purchase1, purchase5)
        self.assertNotEqual(purchase1, purchase3)
        self.assertNotEqual(purchase3, purchase5)

        self.assertEqual(purchase1.date_order[:10], '3003-08-22')
        self.assertEqual(purchase3.date_order[:10], '3003-09-12')
        self.assertEqual(purchase5.date_order[:10], '3003-09-05')

    def test_40_schedule_do_not_ignore_past_procurements(self):
        """Test of scheduling past procurements with 'ignore past procurements' not activated"""

        configuration_wizard = self.env['purchase.config.settings'].create({'ignore_past_procurements': False,
                                                                            'delta_begin_grouping_period': 4})
        configuration_wizard.execute()

        past_proc = self.env['procurement.order'].create({
            'name': 'Procurement order 1 (Purchase Procurement JIT)',
            'product_id': self.product1.id,
            'product_qty': 34,
            'warehouse_id': self.warehouse.id,
            'location_id': self.location_a.id,
            'date_planned': '2016-09-04 15:00:00',
            'product_uom': self.product_uom.id,
        })

        past_proc.run()
        self.assertEqual(past_proc.state, 'buy_to_run')

        self.env['procurement.order'].purchase_schedule(jobify=False)
        purchase0 = past_proc.purchase_id
        purchase1 = self.proc1.purchase_id
        purchase2 = self.proc2.purchase_id
        purchase3 = self.proc3.purchase_id
        purchase5 = self.proc5.purchase_id

        self.assertTrue(purchase0)
        self.assertTrue(purchase1)
        self.assertTrue(purchase2)
        self.assertTrue(purchase3)
        self.assertTrue(purchase5)

        self.assertEqual(purchase2, purchase1)
        self.assertNotEqual(purchase1, purchase5)
        self.assertNotEqual(purchase1, purchase3)
        self.assertNotEqual(purchase3, purchase5)
        self.assertNotEqual(purchase0, purchase1)
        self.assertNotEqual(purchase0, purchase3)
        self.assertNotEqual(purchase0, purchase5)

        date_ref_plus_1_day = self.supplier.schedule_working_days(5, dt.today())
        date_ref = self.supplier.schedule_working_days(4, dt.today())
        date_order, _ = self.frame_week.get_start_end_dates(date_ref_plus_1_day, date_ref=date_ref)
        date_order = fields.Datetime.to_string(date_order)

        self.assertEqual(purchase0.date_order[:10], date_order[:10])
        self.assertEqual(purchase1.date_order[:10], '3003-08-22')
        self.assertEqual(purchase3.date_order[:10], '3003-09-12')

    def test_50_schedule_with_existing_po(self):
        """Test of purchase order line assignation/creation when there are some PO at the beginning."""
        self.env['procurement.order'].purchase_schedule(compute_all_products=False, compute_product_ids=self.product1,
                                                        jobify=False)

        purchase1 = self.proc1.purchase_id
        purchase2 = self.proc2.purchase_id
        purchase3 = self.proc3.purchase_id
        purchase5 = self.proc5.purchase_id

        self.assertTrue(purchase1)
        self.assertTrue(purchase2)
        self.assertTrue(purchase3)
        self.assertTrue(purchase5)

        self.assertEqual(purchase2, purchase1)
        self.assertNotEqual(purchase1, purchase5)
        self.assertNotEqual(purchase1, purchase3)
        self.assertNotEqual(purchase3, purchase5)

        self.assertEqual(purchase1.date_order[:10], '3003-08-22')
        self.assertEqual(purchase3.date_order[:10], '3003-09-12')
        self.assertEqual(purchase5.date_order[:10], '3003-09-05')

        # Let's increase line, confirm a PO in the middle and receive a part of a line
        line5 = purchase5.order_line
        self.assertEqual(len(line5), 1)
        self.assertEqual(line5.product_qty, 36)
        line5.product_qty = 50
        purchase5.signal_workflow('purchase_confirm')
        self.assertEqual(purchase5.state, 'approved')
        move5 = self.env['stock.move'].search([('procurement_id', '=', self.proc5.id)])
        self.assertEqual(len(move5), 1)
        self.assertEqual(move5.purchase_line_id, line5)
        move5.action_done()
        self.assertEqual(self.proc5.state, 'done')
        self.assertEqual(line5.remaining_qty, 46)

        # Let's change a date and reschedule.
        self.proc1.date_planned = '3003-09-14 12:02:05'
        # Now, proc1 is at the same date as purchase5. It should be assigned to purchase5 which is running and not to
        # purchase1 which is draft, and moves should be created for it.

        self.env['procurement.order'].purchase_schedule(compute_all_products=False, compute_product_ids=self.product1,
                                                        jobify=False)

        line5 = purchase5.order_line
        self.assertEqual(len(line5), 1)

        purchase1 = self.proc1.purchase_id
        purchase2 = self.proc2.purchase_id
        purchase3 = self.proc3.purchase_id

        self.assertTrue(purchase1)
        self.assertTrue(purchase3)

        self.assertEqual(purchase2, purchase1)
        self.assertEqual(purchase1, purchase5)
        self.assertNotEqual(purchase3, purchase1)
        self.assertNotEqual(purchase3, purchase5)

        # Let's check moves and procurements for line5
        moves_data = [(move.procurement_id, move.state, move.product_uom_qty) for move in line5.move_ids]
        self.assertIn((self.proc5, 'done', 4), moves_data)
        self.assertIn((self.proc1, 'assigned', 34), moves_data)
        self.assertIn((self.proc2, 'assigned', 2), moves_data)
        self.assertIn((self.env['procurement.order'], 'assigned', 10), moves_data)

        procs_data = [(proc, proc.state, proc.product_qty) for proc in line5.procurement_ids]
        self.assertIn((self.proc5, 'done', 4), procs_data)
        self.assertIn((self.proc1, 'running', 34), procs_data)
        self.assertIn((self.proc2, 'running', 2), procs_data)

    def test_55_schedule_with_existing_po(self):
        """Test of purchase order line assignation/creation when there are some PO at the beginning."""
        self.env['procurement.order'].purchase_schedule(compute_all_products=False, compute_product_ids=self.product1,
                                                        jobify=False)

        purchase1 = self.proc1.purchase_id
        purchase2 = self.proc2.purchase_id
        purchase3 = self.proc3.purchase_id
        purchase5 = self.proc5.purchase_id

        self.assertTrue(purchase1)
        self.assertTrue(purchase2)
        self.assertTrue(purchase3)
        self.assertTrue(purchase5)

        self.assertEqual(purchase2, purchase1)
        self.assertNotEqual(purchase1, purchase5)
        self.assertNotEqual(purchase1, purchase3)
        self.assertNotEqual(purchase3, purchase5)

        self.assertEqual(purchase1.date_order[:10], '3003-08-22')
        self.assertEqual(purchase3.date_order[:10], '3003-09-12')
        self.assertEqual(purchase5.date_order[:10], '3003-09-05')

        # Let's increase line, confirm a PO in the middle and receive a part of a line
        line1 = purchase1.order_line
        self.assertEqual(len(line1), 1)
        self.assertEqual(line1.product_qty, 36)
        line1.product_qty = 35
        purchase1.signal_workflow('purchase_confirm')
        self.assertEqual(purchase1.state, 'approved')
        self.env['procurement.order'].purchase_schedule(compute_all_products=False, compute_product_ids=self.product1,
                                                        jobify=False)

        line1.product_qty = 40

        self.assertEqual(len(line1.procurement_ids), 1)
        self.assertEqual(line1.procurement_ids[0], self.proc1)
        self.assertEqual(len(line1.move_ids), 2)
        m1, m2 = [self.env['stock.move']] * 2
        for move in line1.move_ids:
            if move.product_qty == 34:
                m1 = move
            elif move.product_qty == 6:
                m2 = move

        picking = purchase1.picking_ids[0]
        picking.do_prepare_partial()
        self.assertEqual(len(picking.pack_operation_ids), 1)
        picking.pack_operation_ids[0].product_qty = 35
        picking.do_transfer()

        self.assertEqual(len(line1.move_ids), 3)
        self.assertEqual(m1.state, 'done')
        self.assertEqual(m1.product_qty, 34)
        self.assertEqual(m2.state, 'done')
        self.assertEqual(m2.product_qty, 1)

        self.assertEqual(line1.remaining_qty, 5)

        self.env['procurement.order'].purchase_schedule(compute_all_products=False, compute_product_ids=self.product1,
                                                        jobify=False)
        self.assertEqual(len(line1.procurement_ids), 2)
        self.assertIn(self.proc1, line1.procurement_ids)
        self.assertIn(self.proc2, line1.procurement_ids)
        self.assertNotIn(self.proc3, line1.procurement_ids)

    def test_60_move_change_running_procurement_of_order(self):
        """Test rescheduling to a draft order a procurement which has running moves linked"""
        self.env['procurement.order'].purchase_schedule(jobify=False)

        purchase1 = self.proc1.purchase_id
        purchase3 = self.proc3.purchase_id
        purchase5 = self.proc5.purchase_id

        self.assertTrue(purchase1)
        self.assertTrue(purchase3)
        self.assertTrue(purchase5)

        self.assertNotEqual(purchase1, purchase5)
        self.assertNotEqual(purchase1, purchase3)
        self.assertNotEqual(purchase3, purchase5)

        self.assertEqual(purchase1.date_order[:10], '3003-08-22')
        self.assertEqual(purchase3.date_order[:10], '3003-09-12')
        self.assertEqual(purchase5.date_order[:10], '3003-09-05')

        # Let's confirm purchase1 and create moves for proc1
        line1 = purchase1.order_line.filtered(lambda line: line.product_id == self.product1)
        self.assertEqual(len(line1), 1)
        line1_id = line1.id
        self.assertEqual(line1.product_qty, 36)

        # Let's make an extra move with no proc
        line1.product_qty = 40
        purchase1.signal_workflow('purchase_confirm')
        self.assertEqual(purchase1.state, 'approved')
        move1 = self.env['stock.move'].search([('procurement_id', '=', self.proc1.id)])
        self.assertEqual(len(move1), 1)
        move2 = self.env['stock.move'].search([('procurement_id', '=', self.proc2.id)])
        self.assertEqual(len(move2), 1)
        self.assertEqual(len(line1.move_ids), 3)
        self.assertIn(move1, line1.move_ids)
        extra_move1 = line1.move_ids.filtered(lambda move: move not in [move1, move2])
        self.assertTrue(extra_move1)
        extra_move1_id = extra_move1.id
        group1 = move1.group_id
        picking1 = move1.picking_id
        self.assertTrue(group1)
        self.assertTrue(picking1)

        # We create another move for picking1, so that we can check new moves of line1 are assigned to it
        phantom_move = self.env['stock.move'].create({
            'name': "Incoming move for product 2",
            'product_id': self.product2.id,
            'product_uom_qty': 10,
            'product_uom': self.unit.id,
            'location_id': self.loc_supplier.id,
            'location_dest_id': self.location_a.id,
            'group_id': group1.id,
            'picking_type_id': self.picking_type_in.id,
        })
        phantom_move.action_confirm()
        self.assertEqual(phantom_move.picking_id, picking1)

        # Let's change a date, duplicate proc 1 to swith proc 1 to a draft order (purchase5) and reschedule
        self.proc1.date_planned = '3003-09-14 11:58:22'
        self.assertNotEqual(extra_move1.state, 'cancel')
        self.assertFalse(extra_move1.procurement_id)
        new_proc1 = self.prepare_proc_1()
        new_proc1.run()
        self.assertEqual(new_proc1.state, 'buy_to_run')
        self.env['procurement.order'].purchase_schedule(jobify=False)

        # line1 should still exist
        self.assertIn(line1_id, [line.id for line in self.env['purchase.order.line'].search([])])
        # extra_move1 should have been deleted
        self.assertNotIn(extra_move1_id, [move.id for move in self.env['stock.move'].search([])])

        # Let's check purchase1 moves
        self.assertEqual(len(line1.move_ids), 3)
        moves_data = [(move.procurement_id, move.state, move.product_uom_qty, move.group_id, move.picking_id) for
                      move in line1.move_ids]
        self.assertIn((new_proc1, 'assigned', 34, group1, picking1), moves_data)
        self.assertIn((self.proc2, 'assigned', 2, group1, picking1), moves_data)
        self.assertIn((self.env['procurement.order'], 'assigned', 4, group1, picking1), moves_data)

        # Let's check data for proc1
        purchase5 = self.proc5.purchase_id
        self.assertEqual(purchase5.date_order[:10], '3003-09-05')
        self.assertEqual(purchase5.state, "draft")
        line5 = purchase5.order_line
        self.assertEqual(len(line5), 1)
        self.assertEqual(line5.state, "draft")
        self.assertEqual(self.proc1.purchase_id, purchase5)
        self.assertEqual(self.proc1.purchase_line_id, line5)
        self.assertEqual(len(self.proc1.move_ids), 0)

    def test_70_reschedule_after_proc_removal(self):
        """Test of purchase scheduler after procurement reduction."""
        self.env['procurement.order'].purchase_schedule(compute_all_products=False, compute_supplier_ids=self.supplier,
                                                        jobify=False)
        purchase1 = self.proc1.purchase_id
        purchase2 = self.proc2.purchase_id
        purchase3 = self.proc3.purchase_id
        purchase5 = self.proc5.purchase_id

        self.assertTrue(purchase1)
        self.assertTrue(purchase2)
        self.assertTrue(purchase3)
        self.assertTrue(purchase5)

        self.assertEqual(purchase2, purchase1)
        self.assertNotEqual(purchase1, purchase5)
        self.assertNotEqual(purchase1, purchase3)
        self.assertNotEqual(purchase3, purchase5)

        self.assertEqual(purchase1.date_order[:10], '3003-08-22')
        self.assertEqual(purchase3.date_order[:10], '3003-09-12')
        self.assertEqual(purchase5.date_order[:10], '3003-09-05')

        # Validate order 1 and 3
        purchase1.signal_workflow('purchase_confirm')
        self.assertEqual(len(purchase1.order_line), 1)
        line = purchase1.order_line[0]
        self.assertEqual(sum(m.product_uom_qty for m in line.move_ids), 36)
        self.assertEqual(line.remaining_qty, 36)

        purchase3.signal_workflow('purchase_confirm')
        self.assertEqual(len(purchase3.order_line), 1)
        line3 = purchase3.order_line[0]
        self.assertEqual(sum(m.product_uom_qty for m in line3.move_ids), 36)
        self.assertEqual(line3.remaining_qty, 36)

        # Receive part of the quantity

        # Let's cancel all procurements and reschedule
        self.proc1.cancel()
        self.proc2.cancel()
        self.proc4.cancel()
        self.env['procurement.order'].purchase_schedule(compute_all_products=False, compute_supplier_ids=self.supplier,
                                                        jobify=False)

        # Check that move quantities are OK
        self.assertTrue(purchase1)
        self.assertEqual(len(purchase1.order_line), 1)
        line = purchase1.order_line[0]
        self.assertEqual(sum(m.product_uom_qty for m in line.move_ids), 36)
        self.assertEqual(line.remaining_qty, 36)

        self.assertTrue(purchase3)
        self.assertEqual(len(purchase3.order_line), 1)
        line3 = purchase3.order_line[0]
        self.assertEqual(sum(m.product_uom_qty for m in line3.move_ids), 36)
        self.assertEqual(line3.remaining_qty, 36)
