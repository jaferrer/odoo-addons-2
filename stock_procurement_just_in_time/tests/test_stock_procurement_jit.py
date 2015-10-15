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


class TestStockProcurementJIT(common.TransactionCase):

    def setUp(self):
        super(TestStockProcurementJIT, self).setUp()
        self.test_product = self.browse_ref("stock_procurement_just_in_time.product_test_product")
        self.test_product2 = self.browse_ref("stock_procurement_just_in_time.product_test_product2")
        self.location_a = self.browse_ref("stock_procurement_just_in_time.stock_location_a")
        self.location_b = self.browse_ref("stock_procurement_just_in_time.stock_location_b")
        self.location_inv = self.browse_ref("stock.location_inventory")
        self.product_uom_unit_id = self.ref("product.product_uom_unit")

    def process_orderpoints(self):
        """Function to call the scheduler without needing connector to work."""
        ops = self.env['stock.warehouse.orderpoint'].search([])
        compute_wizard = self.env['procurement.order.compute.all'].create({
            'compute_all': False,
            'product_ids': [(4, self.test_product.id)],
        })
        self.env['procurement.order'].with_context(compute_product_ids=compute_wizard.product_ids.ids,
                                                   compute_all_products=compute_wizard.compute_all,
                                                   without_job=True)._procure_orderpoint_confirm()

    def test_10_procurement_jit_basic(self):
        """Check basic jit procurement from scratch."""
        # Create procurements from minimum stock rules in B
        self.process_orderpoints()
        # Let's have a look to the procurements created in B
        procs = self.env['procurement.order'].search([('location_id', '=', self.location_b.id),
                                                      ('product_id', 'in', [self.test_product.id,
                                                                            self.test_product2.id])])
        procs = procs.sorted(lambda x: x.date_planned)
        self.assertEqual(len(procs), 3)
        # They should all be running
        for proc in procs:
            self.assertEqual(proc.state, 'running')
        self.assertEqual(procs[0].date_planned, "2015-03-15 09:59:59")
        self.assertEqual(procs[0].product_qty, 8)
        self.assertEqual(procs[1].date_planned, "2015-03-20 09:59:59")
        self.assertEqual(procs[1].product_qty, 6)
        self.assertEqual(procs[2].date_planned, "2015-03-25 09:59:59")
        self.assertEqual(procs[2].product_qty, 12)

    def test_20_procurement_jit_reschedule(self):
        """Check jit with rescheduling of confirmed procurement."""
        # Check that procurement_jit is not installed, otherwise this test is useless
        if self.env['ir.module.module'].search([('name', '=', 'procurement_jit'), ('state', '=', 'installed')]):
            self.skipTest("Procurement JIT module is installed")
        proc_env = self.env['procurement.order']
        proc0 = proc_env.create({
            'name': "Procurement 1",
            'date_planned': '2015-03-19 18:00:00',
            'product_id': self.test_product.id,
            'product_qty': 5,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })
        proc1 = proc_env.create({
            'name': "Procurement 2",
            'date_planned': '2015-03-26 18:00:00',
            'product_id': self.test_product2.id,
            'product_qty': 5,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })
        self.process_orderpoints()
        procs = proc_env.search([('location_id', '=', self.location_b.id), ('product_id', 'in', [self.test_product.id,
                                                                            self.test_product2.id])])
        procs = procs.sorted(lambda x: x.date_planned)
        self.assertEqual(len(procs), 4)
        self.assertEqual(procs[0], proc0)
        self.assertEqual(procs[0].date_planned, "2015-03-15 09:59:59")
        self.assertEqual(procs[0].product_qty, 5)
        self.assertEqual(procs[0].state, 'confirmed')
        self.assertEqual(procs[1].date_planned, "2015-03-20 09:59:59")
        self.assertEqual(procs[1].product_qty, 8)
        self.assertEqual(procs[1].state, 'running')
        self.assertEqual(procs[2].date_planned, "2015-03-25 09:59:59")
        self.assertEqual(procs[2].product_qty, 14)
        self.assertEqual(procs[2].state, 'running')
        self.assertEqual(procs[3].date_planned, "2015-03-26 18:00:00")
        self.assertEqual(procs[3].product_qty, 5)

    def test_30_procurement_jit_several_reschedule(self):
        """Check jit with several rescheduling of running procurements."""
        proc_env = self.env['procurement.order']
        proc0 = proc_env.create({
            'name': "Procurement 1",
            'date_planned': '2015-03-26 00:00:00',
            'product_id': self.test_product.id,
            'product_qty': 3,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })
        proc0.run()
        self.assertEqual(proc0.move_ids[0].date[0:10], "2015-03-19")
        proc1 = proc_env.create({
            'name': "Procurement 2",
            'date_planned': '2015-03-30 00:00:00',
            'product_id': self.test_product.id,
            'product_qty': 3,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })
        proc1.run()
        self.assertEqual(proc1.move_ids[0].date[0:10], "2015-03-23")
        self.process_orderpoints()
        procs = proc_env.search([('location_id', '=', self.location_b.id), ('product_id', '=', self.test_product.id)])
        procs = procs.sorted(lambda x: x.date_planned)
        # They should all be running
        for proc in procs:
            self.assertEqual(proc.state, 'running')
        self.assertEqual(len(procs), 4)
        self.assertIn(proc0, [procs[0], procs[1]])
        self.assertIn(proc1, [procs[0], procs[1]])
        self.assertEqual(proc0.date_planned, "2015-03-15 09:59:59")
        self.assertEqual(proc0.product_qty, 3)
        for move in proc0.move_ids:
            self.assertEqual(move.date[:10], "2015-03-09")
            self.assertEqual(move.date_expected[:10], "2015-03-09")
        self.assertEqual(proc1.date_planned, "2015-03-15 09:59:59")
        for move in proc1.move_ids:
            self.assertEqual(move.date[:10], "2015-03-09")
            self.assertEqual(move.date_expected[:10], "2015-03-09")
        self.assertEqual(proc1.product_qty, 3)
        self.assertEqual(procs[2].date_planned, "2015-03-20 09:59:59")
        self.assertEqual(procs[2].product_qty, 8)
        self.assertEqual(procs[3].date_planned, "2015-03-25 09:59:59")
        self.assertEqual(procs[3].product_qty, 12)

    def test_40_procurement_jit_with_fixed_in_moves(self):
        """Check jit with fixed incoming moves in the middle."""
        proc_env = self.env['procurement.order']
        proc0 = proc_env.create({
            'name': "Procurement 1",
            'date_planned': '2015-03-23 00:00:00',
            'product_id': self.test_product.id,
            'product_qty': 4,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })
        move = self.env["stock.move"].create({
            'name': "Incoming move",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 3,
            'location_id': self.location_inv.id,
            'location_dest_id': self.location_b.id,
            'date': "2015-03-19 12:00:00",
        })
        move.action_confirm()
        self.process_orderpoints()
        procs = proc_env.search([('location_id', '=', self.location_b.id), ('product_id', '=', self.test_product.id)])
        procs = procs.sorted(lambda x: x.date_planned)
        self.assertEqual(len(procs), 3)
        self.assertEqual(procs[0], proc0)
        self.assertEqual(procs[0].date_planned, "2015-03-15 09:59:59")
        self.assertEqual(procs[0].product_qty, 4)
        if self.env['ir.module.module'].search([('name', '=', 'procurement_jit'), ('state', '=', 'installed')]):
            self.assertEqual(procs[0].state, 'running')
        else:
            self.assertEqual(procs[0].state, 'confirmed')
        self.assertEqual(procs[1].date_planned, "2015-03-20 09:59:59")
        self.assertEqual(procs[1].product_qty, 6)
        self.assertEqual(procs[1].state, 'running')
        self.assertEqual(procs[2].date_planned, "2015-03-25 09:59:59")
        self.assertEqual(procs[2].product_qty, 14)
        self.assertEqual(procs[2].state, 'running')

    def test_50_procurement_jit_oversupply(self):
        """Test redistribution of procurements when the location is over supplied."""
        proc_env = self.env['procurement.order']
        # First let's start with the basic procurement scenario
        self.test_10_procurement_jit_basic()
        move_need2 = self.browse_ref('stock_procurement_just_in_time.need2')
        move_need2.date = "2015-03-27 11:00:00"
        # We create a new move in order to have a need at the end
        new_move = move_need2.copy({'date': "2015-03-30 11:10:00"})
        new_move.action_confirm()
        self.process_orderpoints()
        procs = proc_env.search([('location_id', '=', self.location_b.id), ('product_id', '=', self.test_product.id)])
        procs = procs.sorted(lambda x: x.date_planned)
        self.assertEqual(len(procs), 4)
        for proc in procs:
            self.assertEqual(proc.state, 'running')
        self.assertEqual(procs[0].date_planned, "2015-03-15 09:59:59")
        self.assertEqual(procs[0].product_qty, 8)
        self.assertEqual(procs[1].date_planned, "2015-03-25 09:59:59")
        self.assertEqual(procs[1].product_qty, 12)
        self.assertEqual(procs[2].date_planned, "2015-03-27 10:59:59")
        self.assertEqual(procs[2].product_qty, 6)
        self.assertEqual(procs[3].date_planned, "2015-03-30 11:09:59")
        self.assertEqual(procs[3].product_qty, 6)

    def test_60_procurement_jit_removal(self):
        """Test removal of unecessary procurements at the end."""
        proc_env = self.env['procurement.order']
        # First let's start with the basic procurement scenario
        self.test_10_procurement_jit_basic()
        move_need2 = self.browse_ref('stock_procurement_just_in_time.need2')
        move_need2.action_cancel()
        self.process_orderpoints()
        procs = proc_env.search([('location_id', '=', self.location_b.id), ('product_id', '=', self.test_product.id)])
        procs = procs.sorted(lambda x: x.date_planned)
        self.assertEqual(len(procs), 2)
        for proc in procs:
            self.assertEqual(proc.state, 'running')
        self.assertEqual(procs[0].date_planned, "2015-03-15 09:59:59")
        self.assertEqual(procs[0].product_qty, 8)
        self.assertEqual(procs[1].date_planned, "2015-03-25 09:59:59")
        self.assertEqual(procs[1].product_qty, 12)
