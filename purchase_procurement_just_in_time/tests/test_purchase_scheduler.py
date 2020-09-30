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
from openerp.tools.misc import frozendict


class TestPurchaseScheduler(common.TransactionCase):
    def setUp(self):
        super(TestPurchaseScheduler, self).setUp()
        self.env.context = frozendict(dict(self.env.context, check_product_qty=False))
        self.company = self.browse_ref('base.main_company')
        self.company.write({'po_lead': 5})
        self.supplier = self.browse_ref('purchase_procurement_just_in_time.supplier1')
        self.supplier2 = self.browse_ref('purchase_procurement_just_in_time.supplier2')
        self.supplier_no_order = self.browse_ref('purchase_procurement_just_in_time.supplier_no_order')
        self.product1 = self.browse_ref('purchase_procurement_just_in_time.product1')
        self.product2 = self.browse_ref('purchase_procurement_just_in_time.product2')
        self.supplierinfo2 = self.browse_ref('purchase_procurement_just_in_time.supplierinfo2')
        self.product_uom = self.browse_ref('product.product_uom_unit')
        self.location_a = self.browse_ref('purchase_procurement_just_in_time.stock_location_a')
        self.location_b = self.browse_ref('purchase_procurement_just_in_time.stock_location_b')
        self.warehouse = self.browse_ref('stock.warehouse0')
        self.frame_week = self.browse_ref('purchase_procurement_just_in_time.week')
        self.loc_supplier = self.browse_ref('stock.stock_location_suppliers')
        self.picking_type_in = self.browse_ref('stock.picking_type_in')
        self.unit = self.browse_ref('product.product_uom_unit')
        self.uom_couple = self.browse_ref('purchase_procurement_just_in_time.uom_couple')
        self.uom_four = self.browse_ref('purchase_procurement_just_in_time.uom_four')
        self.cron_stock_scheduler = self.browse_ref('stock_procurement_just_in_time.job_update_scheduler_controller')
        self.cron_stock_scheduler.active = False
        self.env['stock.scheduler.controller'].search([]).write({'done': True})

        self.prepare_procurements()

        configuration_wizard = self.env['purchase.config.settings']. \
            create({'delta_begin_grouping_period': False, 'ignore_past_procurements': False})
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

    def create_move_out_corresponding_to_procs(self):
        self.env['stock.move'].search([('origin', '=', 'to_remove'),
                                       ('state', 'not in', ['cancel', 'done'])]).action_cancel()
        for proc in self.env['procurement.order'].search([('state', 'not in', ['done', 'cancel']),
                                                          ('location_id', '=', self.location_a.id),
                                                          ('rule_id.action', '=', 'buy')]):
            if not proc.move_dest_id:
                move = self.env['stock.move'].create({
                    'name': "Outgoing move corresponding to proc %s" % proc.display_name,
                    'product_id': proc.product_id.id,
                    'product_uom_qty': proc.product_qty,
                    'product_uom': proc.product_uom.id,
                    'location_id': self.location_a.id,
                    'location_dest_id': self.location_b.id,
                    'date': proc.date_planned,
                    'origin': 'to_remove'
                })
                move.action_confirm()
                self.assertEqual(move.state, 'confirmed')
        self.env.invalidate_all()

    def test_10_schedule_and_reschedule_from_scratch(self):
        """Test of purchase order creation from scratch when there are none at the beginning."""
        self.company.write({'po_lead': 3})
        self.supplier.write({'purchase_lead_time': 2})
        self.create_move_out_corresponding_to_procs()
        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_supplier_ids=self.supplier,
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

        self.assertEqual(2, len(purchase1.order_line))
        for line in purchase1.order_line:
            if line.product_id == self.product1:
                self.assertEqual('3003-09-14', line.covering_date)
                self.assertEqual('coverage_computed', line.covering_state)
            if line.product_id == self.product2:
                self.assertFalse(line.covering_date)
                self.assertEqual('all_covered', line.covering_state)
        self.assertFalse(purchase3.order_line.covering_date)
        self.assertEqual('all_covered', purchase3.order_line.covering_state)
        self.assertEqual('3003-09-22', purchase5.order_line.covering_date)
        self.assertEqual('coverage_computed', purchase5.order_line.covering_state)

        # Let's change a date and reschedule
        self.proc1.date_planned = '3003-09-23 12:00:00'
        self.create_move_out_corresponding_to_procs()
        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_supplier_ids=self.supplier,
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

        self.assertFalse(purchase1.order_line.covering_date)
        self.assertEqual('all_covered', purchase1.order_line.covering_state)
        self.assertEqual('3003-09-22', purchase2.order_line.covering_date)
        self.assertEqual('coverage_computed', purchase2.order_line.covering_state)

        purchase1.compute_coverage_state()
        self.assertEqual('all_covered', purchase1.order_line.covering_state)
        self.assertFalse(purchase1.order_line.covering_date)
        purchase2.compute_coverage_state()
        self.assertEqual('coverage_computed', purchase2.order_line.covering_state)
        self.assertEqual('3003-09-22', purchase2.order_line.covering_date)

    def test_11_schedule_a_limited_number_of_orders(self):
        """Test of purchase order creation from scratch when nb_max_draft_orders is defined for the suplier."""
        self.supplier.nb_max_draft_orders = 2
        order_other_supplier = self.env['purchase.order'].create({'partner_id': self.supplier2.id,
                                                                  'location_id': self.location_a.id,
                                                                  'pricelist_id': self.ref('purchase.list0')})

        pol = self.env['purchase.order.line'].create({'name': "product 1",
                                                      'product_id': self.product1.id,
                                                      'date_planned': "2016-12-01",
                                                      'order_id': order_other_supplier.id,
                                                      'price_unit': 2,
                                                      'product_qty': 10})

        before_split = self.proc1.product_qty

        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_product_ids=self.product1,
                                                        jobify=False)

        proc_split = self.env['procurement.order'].search([('purchase_line_id', '=', pol.id),
                                                           ('state', 'not in', ['done', 'cancel'])])

        purchase1 = self.proc1.purchase_id
        purchase2 = self.proc2.purchase_id
        purchase3 = self.proc3.purchase_id
        purchase5 = self.proc5.purchase_id

        self.assertTrue(purchase1)
        self.assertTrue(purchase2)
        self.assertFalse(purchase3)
        self.assertTrue(purchase5)

        self.assertTrue(proc_split)
        self.assertEqual(proc_split.split_from_id, self.proc1)
        all_prod_qty = self.proc1.product_qty + proc_split.product_qty
        self.assertEqual(before_split, all_prod_qty)

        self.assertEqual(purchase2, purchase1, purchase5)
        self.assertEqual(purchase1.date_order[:10], '3003-08-22')

        other_draft_order = self.env['purchase.order'].search([('state', '=', 'draft'),
                                                               ('order_line', '=', False)])
        self.assertEqual(len(other_draft_order), 1)
        self.assertEqual(other_draft_order.date_order[:10], '3003-08-29')

    def test_12_schedule_a_limited_number_of_orders_with_dates(self):
        """Test of purchase order creation from scratch when nb_max_draft_orders is defined for the suplier, and
        when procurements are really distant."""
        self.supplier.nb_max_draft_orders = 2

        # Proc 6 will now be the latest order by date planned. But its purchase date will be between the two first
        # orders or product 1
        self.proc6.date_planned = '3003-09-25 15:00:00'
        self.supplierinfo2.delay += 8

        self.env['procurement.order'].purchase_schedule(compute_all_products=True,
                                                        compute_product_ids=self.product1 + self.product2,
                                                        jobify=False)
        purchase1 = self.proc1.purchase_id
        purchase2 = self.proc2.purchase_id
        purchase3 = self.proc3.purchase_id
        purchase5 = self.proc5.purchase_id
        purchase6 = self.proc6.purchase_id

        self.assertTrue(purchase1)
        self.assertTrue(purchase2)
        self.assertFalse(purchase3)
        self.assertFalse(purchase5)
        self.assertTrue(purchase6)

        self.assertEqual(purchase2, purchase1)
        self.assertNotEqual(purchase1, purchase6)

        self.assertEqual(purchase1.date_order[:10], '3003-08-22')
        self.assertEqual(purchase6.date_order[:10], '3003-08-29')

    def test_20_schedule_ignore_past_procurements(self):
        """Test of scheduling past procurements with 'ignore past procurements' activated"""

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

        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_product_ids=self.product1,
                                                        compute_supplier_ids=self.supplier, jobify=False)
        past_purchase = past_proc.purchase_id
        purchase1 = self.proc1.purchase_id
        purchase2 = self.proc2.purchase_id
        purchase3 = self.proc3.purchase_id
        purchase5 = self.proc5.purchase_id

        self.assertTrue(past_purchase)
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

        self.assertEqual(past_proc.state, 'running')

        configuration_wizard = self.env['purchase.config.settings'].create({'ignore_past_procurements': True})
        configuration_wizard.execute()
        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_product_ids=self.product1,
                                                        compute_supplier_ids=self.supplier, jobify=False)
        past_purchase = past_proc.purchase_id
        purchase1 = self.proc1.purchase_id
        purchase2 = self.proc2.purchase_id
        purchase3 = self.proc3.purchase_id
        purchase5 = self.proc5.purchase_id

        self.assertFalse(past_purchase)
        self.assertFalse(past_proc.move_ids)
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

        self.assertEqual(past_proc.state, 'buy_to_run')

    def test_21_schedule_do_not_ignore_past_procurements(self):
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

        date_ref = self.supplier.schedule_working_days(4, dt.today())
        date_order, _ = self.frame_week.get_start_end_dates(date_ref, date_ref=date_ref)
        date_order = fields.Datetime.to_string(date_order)

        self.assertEqual(purchase0.date_order[:10], date_order[:10])
        self.assertEqual(purchase1.date_order[:10], '3003-08-22')
        self.assertEqual(purchase3.date_order[:10], '3003-09-12')

    def test_22_schedule_with_existing_po(self):
        """Test of purchase order line assignation/creation when there are some PO at the beginning."""
        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_product_ids=self.product1,
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
        move5 = line5.move_ids
        self.assertEqual(len(move5), 1)
        # We check uom treatment for function compute_procs_for_first_line_found
        self.assertEqual(self.proc1.product_qty, 34)
        self.assertEqual(self.proc1.product_uom, self.unit)
        self.proc1.product_qty = 17
        self.proc1.product_uom = self.uom_couple
        self.assertEqual(len(move5), 1)
        self.assertEqual(move5.purchase_line_id, line5)
        # Let's transfer 4 units (qty of proc 5).
        new_move_id = self.env['stock.move'].split(move5, 4)
        new_move = self.env['stock.move'].browse(new_move_id)
        self.assertEqual(new_move.purchase_line_id, line5)
        new_move.action_done()
        self.assertEqual(self.proc5.state, 'done')
        self.assertEqual(line5.remaining_qty, 46)

        # Let's change a date and reschedule.
        self.proc1.date_planned = '3003-09-14 12:02:05'
        # Now, proc1 is at the same date as purchase5. It should be assigned to purchase5 which is running and not to
        # purchase1 which is draft, and moves should be created for it.

        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_product_ids=self.product1,
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
        self.assertIn((self.env['procurement.order'], 'done', 4), moves_data)
        self.assertIn((self.env['procurement.order'], 'assigned', 46), moves_data)

        procs_data = [(proc, proc.state, proc.product_qty, proc.product_uom) for proc in line5.procurement_ids]
        self.assertIn((self.proc5, 'done', 4, self.unit), procs_data)
        self.assertIn((self.proc1, 'running', 17, self.uom_couple), procs_data)
        self.assertIn((self.proc2, 'running', 2, self.unit), procs_data)

    def test_23_schedule_with_existing_po(self):
        """Test of purchase order line assignation/creation when there are some PO at the beginning."""
        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_product_ids=self.product1,
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
        self.assertEqual(len(line1.procurement_ids), 2)
        self.assertIn(self.proc1, line1.procurement_ids)
        self.assertIn(self.proc2, line1.procurement_ids)
        line1.product_qty = 35

        purchase1.signal_workflow('purchase_confirm')
        self.assertEqual(purchase1.state, 'approved')
        self.assertEqual(len(line1.move_ids), 1)
        self.assertEqual(line1.move_ids.product_qty, 35)
        self.assertFalse(line1.move_ids.procurement_id)
        # No proc was removed from this line (this will be done by the next purchase scheduler)
        self.assertEqual(len(line1.procurement_ids), 2)
        self.assertIn(self.proc1, line1.procurement_ids)
        self.assertIn(self.proc2, line1.procurement_ids)

        before_split = self.proc2.product_qty

        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_product_ids=self.product1,
                                                        jobify=False)
        split_proc = self.env['procurement.order'].search([('split_from_id', '=', self.proc2.id)])
        total_proc_split = split_proc.product_qty + self.proc2.product_qty
        self.assertTrue(split_proc)
        # proc2 was splited from this line, and there is still only one move linked
        self.assertEqual(len(line1.procurement_ids), 2)
        self.assertIn(self.proc1, line1.procurement_ids)
        self.assertIn(split_proc, line1.procurement_ids)
        self.assertEqual(before_split, total_proc_split)
        self.assertEqual(len(line1.move_ids), 1)
        self.assertEqual(line1.move_ids.product_qty, 35)
        self.assertFalse(line1.move_ids.procurement_id)

        line1.product_qty = 40

        self.assertEqual(len(line1.procurement_ids), 2)
        self.assertIn(self.proc1, line1.procurement_ids)
        self.assertIn(split_proc, line1.procurement_ids)
        self.assertEqual(len(line1.move_ids.filtered(lambda move: move.state != 'cancel')), 2)
        m1, m2 = [self.env['stock.move']] * 2
        for move in line1.move_ids.filtered(lambda move: move.state != 'cancel'):
            if move.product_qty == 35:
                m1 = move
            elif move.product_qty == 5:
                m2 = move
        self.assertTrue(m1 and m2)

        picking = purchase1.picking_ids[0]
        picking.do_prepare_partial()
        self.assertEqual(len(picking.pack_operation_ids), 1)
        picking.pack_operation_ids[0].product_qty = 35
        picking.do_transfer()

        self.assertEqual(len(line1.move_ids.filtered(lambda move: move.state != 'cancel')), 2)
        self.assertEqual(m1.state, 'done')
        self.assertEqual(m1.product_qty, 35)
        self.assertEqual(m2.state, 'assigned')
        self.assertEqual(m2.product_qty, 5)
        self.assertNotEqual(m1.picking_id, m2.picking_id)

        self.assertEqual(line1.remaining_qty, 5)

        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_product_ids=self.product1,
                                                        jobify=False)
        self.assertEqual(len(line1.procurement_ids), 4)
        self.assertIn(self.proc1, line1.procurement_ids)
        self.assertIn(self.proc2, line1.procurement_ids)
        self.assertIn(self.proc5, line1.procurement_ids)
        self.assertIn(split_proc, line1.procurement_ids)
        proc_line_total = self.proc5.product_qty + self.proc2.product_qty + \
                          self.proc1.product_qty + split_proc.product_qty
        self.assertEqual(proc_line_total, 40)
        self.assertNotIn(self.proc3, line1.procurement_ids)

    def test_24_move_change_running_procurement_of_order(self):
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

        self.assertEqual(purchase1.partner_id, self.supplier)

        # Let's confirm purchase1 and create moves for proc1
        line1 = purchase1.order_line.filtered(lambda line: line.product_id == self.product1)
        self.assertEqual(len(line1), 1)
        line1_id = line1.id
        self.assertEqual(line1.product_qty, 36)

        # Let's make an extra move with no proc
        line1.product_qty = 40
        purchase1.signal_workflow('purchase_confirm')
        self.assertEqual(purchase1.state, 'approved')
        move = line1.move_ids
        self.assertEqual(len(move), 1)
        group1 = move.group_id
        picking1 = move.picking_id
        self.assertEqual(picking1.partner_id, self.supplier)
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
        self.assertNotEqual(move.state, 'cancel')
        self.assertFalse(move.procurement_id)
        new_proc1 = self.prepare_proc_1()
        new_proc1.run()
        self.assertEqual(new_proc1.state, 'buy_to_run')
        self.env['procurement.order'].purchase_schedule(jobify=False)

        # line1 should still exist
        self.assertIn(line1_id, [line.id for line in self.env['purchase.order.line'].search([])])

        # Let's check purchase1 moves
        self.assertEqual(len(line1.move_ids), 1)
        self.assertEqual(line1.move_ids, move)

        # Let's check data for proc1
        purchase5 = self.proc5.purchase_id
        self.assertEqual(purchase5.date_order[:10], '3003-09-05')
        self.assertEqual(purchase5.state, "draft")
        line5 = purchase5.order_line
        self.assertEqual(len(line5), 1)
        self.assertEqual(line5.state, "draft")
        self.assertEqual(self.proc1.purchase_id, purchase5)
        self.assertEqual(self.proc1.purchase_line_id, line5)
        self.assertFalse(self.proc1.move_ids)

    def test_25_switch_proc_from_confirmed_to_sent_order(self):
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
        move = line1.move_ids
        self.assertEqual(len(move), 1)
        group1 = move.group_id
        picking1 = move.picking_id
        self.assertTrue(group1)
        self.assertTrue(picking1)

        # Let's change a date, duplicate proc 1 to swith proc 1 to a draft order (purchase5) and reschedule
        self.proc1.date_planned = '3003-09-14 11:58:22'
        self.assertNotEqual(move.state, 'cancel')
        self.assertFalse(move.procurement_id)

        # Let's switch purchase5 to 'sent' status
        purchase5.state = 'sent'
        self.env['procurement.order'].purchase_schedule(jobify=False)

        # line1 should still exist
        self.assertIn(line1_id, [line.id for line in self.env['purchase.order.line'].search([])])

        # Let's check purchase1 moves
        self.assertEqual(len(line1.move_ids), 1)
        self.assertEqual(line1.move_ids, move)

        # Let's check that sent order still has no picking
        self.assertFalse(purchase5.picking_ids)

        # Let's check data for proc1 and proc3
        self.assertEqual(self.proc5.purchase_id, purchase1)
        self.assertEqual(self.proc3.purchase_id, purchase5)

    def test_26_reschedule_after_proc_removal(self):
        """Test of purchase scheduler after procurement reduction."""
        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_supplier_ids=self.supplier,
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
        self.assertEqual(len(purchase1.order_line), 2)
        line = [pol for pol in purchase1.order_line if pol.product_id == self.product1][0]
        self.assertEqual(sum(m.product_uom_qty for m in line.move_ids), 36)
        self.assertEqual(line.remaining_qty, 36)

        purchase3.signal_workflow('purchase_confirm')
        self.assertEqual(len(purchase3.order_line), 1)
        line3 = purchase3.order_line[0]
        self.assertEqual(sum(m.product_uom_qty for m in line3.move_ids), 36)
        self.assertEqual(line3.remaining_qty, 36)

        # Let's cancel all procurements and reschedule. We also save purchase lines associated with procurements,
        # because we will check they have not changed of procurement after rescheduling.
        purchase_line1 = self.proc1.purchase_line_id
        purchase_line2 = self.proc2.purchase_line_id
        purchase_line4 = self.proc4.purchase_line_id
        self.proc1.cancel()
        self.proc2.cancel()
        self.proc4.cancel()
        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_supplier_ids=self.supplier,
                                                        jobify=False)

        # Check that move quantities are OK
        self.assertTrue(purchase1)
        self.assertEqual(len(purchase1.order_line), 2)
        line = [pol for pol in purchase1.order_line if pol.product_id == self.product1][0]
        self.assertEqual(sum(m.product_uom_qty for m in line.move_ids), 36)
        self.assertEqual(line.remaining_qty, 36)

        self.assertTrue(purchase3)
        self.assertEqual(len(purchase3.order_line), 1)
        line3 = purchase3.order_line[0]
        self.assertEqual(sum(m.product_uom_qty for m in line3.move_ids), 36)
        self.assertEqual(line3.remaining_qty, 36)

        # Check that cancelled procurements did not change of purchase lines
        self.assertEqual(self.proc1.purchase_line_id, purchase_line1)
        self.assertEqual(self.proc2.purchase_line_id, purchase_line2)
        self.assertEqual(self.proc4.purchase_line_id, purchase_line4)

    def test_27_add_grouping_period_to_supplier(self):
        """Test of purchase order creation from scratch when there are none at the beginning."""
        self.supplier.order_group_period = False
        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_supplier_ids=self.supplier,
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

        self.assertEqual(purchase1, purchase2)
        self.assertEqual(purchase1, purchase3)
        self.assertEqual(purchase1, purchase5)
        self.assertEqual(purchase1, purchase6)

        self.assertEqual(purchase1.date_order[:10], fields.Date.today())
        self.assertEqual(len(purchase1.order_line), 2)
        lines_data = [(line.product_id, line.product_qty) for line in purchase1.order_line]
        self.assertIn((self.product1, 84), lines_data)
        self.assertIn((self.product2, 34), lines_data)

        self.supplier.order_group_period = self.frame_week
        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_supplier_ids=self.supplier,
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
        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_supplier_ids=self.supplier,
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

    def test_28_schedule_do_not_ignore_past_procurements_force_dateref(self):
        """Test of scheduling past procurements with 'ignore past procurements' not activated with force dateref"""

        configuration_wizard = self.env['purchase.config.settings'].create({'ignore_past_procurements': False,
                                                                            'delta_begin_grouping_period': 0})
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

        date_ref = self.supplier.schedule_working_days(4, dt.today())

        self.env['procurement.order'].purchase_schedule(jobify=False,
                                                        force_date_ref=fields.Date.to_string(date_ref).split(" ")[0])
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

        date_order, _ = self.frame_week.get_start_end_dates(date_ref, date_ref=date_ref)
        date_order = fields.Datetime.to_string(date_order)

        self.assertEqual(purchase0.date_order[:10], date_order[:10])
        self.assertEqual(purchase1.date_order[:10], '3003-08-22')
        self.assertEqual(purchase3.date_order[:10], '3003-09-12')

    def test_29_schedule_ignore_past_procurements_force_dateref(self):
        """Test of scheduling past procurements with 'ignore past procurements' activated with force dateref"""

        date_ref_tomorrow = self.supplier.schedule_working_days(2, dt.today())
        date_ref = self.supplier.schedule_working_days(1, dt.today())

        past_proc = self.env['procurement.order'].create({
            'name': 'Procurement order 1 (Purchase Procurement JIT)',
            'product_id': self.product1.id,
            'product_qty': 34,
            'warehouse_id': self.warehouse.id,
            'location_id': self.location_a.id,
            'date_planned': fields.Datetime.to_string(date_ref_tomorrow).split(" ")[0] + " 15:00:00",
            'product_uom': self.product_uom.id,
        })

        past_proc.run()
        self.assertEqual(past_proc.state, 'buy_to_run')

        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_product_ids=self.product1,
                                                        compute_supplier_ids=self.supplier, jobify=False,
                                                        force_date_ref=fields.Date.to_string(date_ref).split(" ")[0])
        past_purchase = past_proc.purchase_id
        purchase1 = self.proc1.purchase_id
        purchase2 = self.proc2.purchase_id
        purchase3 = self.proc3.purchase_id
        purchase5 = self.proc5.purchase_id

        self.assertTrue(past_purchase)
        self.assertTrue(purchase1)
        self.assertTrue(purchase2)
        self.assertTrue(purchase3)
        self.assertTrue(purchase5)

        self.assertEqual(purchase2, purchase1)
        self.assertNotEqual(purchase1, purchase5)
        self.assertNotEqual(purchase1, purchase3)
        self.assertNotEqual(purchase3, purchase5)

        date_order, _ = self.frame_week.get_start_end_dates(date_ref, date_ref=date_ref)
        date_order = fields.Datetime.to_string(date_order)

        self.assertEqual(past_purchase.date_order[:10], date_order[:10])
        self.assertEqual(purchase1.date_order[:10], '3003-08-22')
        self.assertEqual(purchase3.date_order[:10], '3003-09-12')
        self.assertEqual(purchase5.date_order[:10], '3003-09-05')

        self.assertEqual(past_proc.state, 'running')

        configuration_wizard = self.env['purchase.config.settings'].create({'ignore_past_procurements': True})
        configuration_wizard.execute()
        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_product_ids=self.product1,
                                                        compute_supplier_ids=self.supplier, jobify=False,
                                                        force_date_ref=fields.Date.to_string(date_ref).split(" ")[0])
        past_purchase = past_proc.purchase_id
        purchase1 = self.proc1.purchase_id
        purchase2 = self.proc2.purchase_id
        purchase3 = self.proc3.purchase_id
        purchase5 = self.proc5.purchase_id

        self.assertFalse(past_purchase)
        self.assertFalse(past_proc.move_ids)
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

        self.assertEqual(past_proc.state, 'buy_to_run')

    def test_30_group_procs_from_different_grouping_periods(self):
        self.company.write({'po_lead': 3})
        self.supplier.write({'purchase_lead_time': 2})
        self.proc3.cancel()
        self.proc5.cancel()
        self.proc6.cancel()
        self.proc2.date_planned = '3005-09-12 15:00:00'
        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_supplier_ids=self.supplier,
                                                        jobify=False)
        purchase1 = self.proc1.purchase_id
        purchase2 = self.proc2.purchase_id

        self.assertTrue(purchase1)
        self.assertTrue(purchase2)
        self.assertEqual(purchase2, purchase1)

        self.assertEqual(purchase1.date_order[:10], '3003-08-22')

    def test_31_compute_first_purchase_date(self):

        # We need a mono-product case
        self.proc6.cancel()

        # We need to fill field "supplier_id" for concerned products
        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_supplier_ids=self.supplier,
                                                        jobify=False)

        procs = self.env['procurement.order'].browse([self.proc1.id, self.proc2.id, self.proc3.id, self.proc5.id])

        first_purchase_dates = procs.get_first_purchase_dates_for_seller(self.supplier)
        self.assertIn(self.company.id, first_purchase_dates.keys())
        self.assertIn(self.location_a.id, first_purchase_dates[self.company.id].keys())
        self.assertIn('first_purchase_date', first_purchase_dates[self.company.id][self.location_a.id].keys())
        date = first_purchase_dates[self.company.id][self.location_a.id]['first_purchase_date']
        self.assertTrue(date)
        self.assertEqual(date[:10], '3003-08-25')

        # Now, let's try with a past procurement
        self.proc1.date_planned = '2018-03-09 12:00:00'
        first_purchase_dates = procs.get_first_purchase_dates_for_seller(self.supplier)
        self.assertIn(self.company.id, first_purchase_dates.keys())
        self.assertIn(self.location_a.id, first_purchase_dates[self.company.id].keys())
        self.assertIn('first_purchase_date', first_purchase_dates[self.company.id][self.location_a.id].keys())
        date = first_purchase_dates[self.company.id][self.location_a.id]['first_purchase_date']
        self.assertTrue(date)
        self.assertEqual(date[:10], fields.Date.today())

    def test_40_delete_order_no_proc(self):
        order_id = self.env['purchase.order'].create({
            'partner_id': self.supplier_no_order.id,
            'location_id': self.location_a.id,
            'pricelist_id': self.ref('purchase.list0')
        }).id
        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_supplier_ids=self.supplier_no_order,
                                                        jobify=False)
        self.assertNotIn(order_id, self.env['purchase.order'].search([]).ids)

    def test_50_temporary_additional_delay(self):
        self.supplier.write({'temporary_additional_delay': 0})
        self.assertEqual(self.supplier.temporary_additional_delay, 0)
        self.create_move_out_corresponding_to_procs()
        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_supplier_ids=self.supplier,
                                                        jobify=False)
        purchase1 = self.proc1.purchase_id
        self.assertTrue(purchase1)
        self.assertEqual(purchase1.date_order, '3003-08-22 00:00:00')

        purchase1.unlink()

        self.supplier.write({'temporary_additional_delay': 5})
        self.assertEqual(self.supplier.temporary_additional_delay, 5)
        self.create_move_out_corresponding_to_procs()
        self.env['procurement.order'].purchase_schedule(compute_all_products=False,
                                                        compute_supplier_ids=self.supplier,
                                                        jobify=False)

        purchase1 = self.proc1.purchase_id
        self.assertTrue(purchase1)
        self.assertEqual(purchase1.date_order, '3003-08-15 00:00:00')
