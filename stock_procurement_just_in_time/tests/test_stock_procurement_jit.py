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

from openerp import fields
from openerp.tests import common


class TestStockProcurementJIT(common.TransactionCase):
    def setUp(self):
        super(TestStockProcurementJIT, self).setUp()
        self.test_product = self.browse_ref("stock_procurement_just_in_time.product_test_product")
        self.test_product2 = self.browse_ref("stock_procurement_just_in_time.product_test_product2")
        self.test_product3 = self.browse_ref("stock_procurement_just_in_time.product_test_product3")
        self.test_product4 = self.browse_ref("stock_procurement_just_in_time.product_test_product4")
        self.warehouse_orderpoint1 = self.browse_ref("stock_procurement_just_in_time.warehouse_orderpoint1")
        self.stock_location_orig = self.browse_ref("stock_procurement_just_in_time.stock_location_orig")
        self.location_a = self.browse_ref("stock_procurement_just_in_time.stock_location_a")
        self.location_b = self.browse_ref("stock_procurement_just_in_time.stock_location_b")
        self.location_inv = self.browse_ref("stock.location_inventory")
        self.product_uom_unit_id = self.ref("product.product_uom_unit")
        self.unit = self.browse_ref('product.product_uom_unit')
        self.stock = self.browse_ref('stock.stock_location_stock')
        self.customer = self.browse_ref('stock.stock_location_customers')
        self.supplier = self.browse_ref('stock.stock_location_suppliers')
        self.rule_move = self.browse_ref('stock_procurement_just_in_time.rule_move')
        # Compute parent left and right for location so that test don't fail
        self.env['stock.location']._parent_store_compute()
        # Configure cancelled moves/procs deletion
        wizard = self.env['stock.config.settings'].create({'delete_moves_cancelled_by_planned': True,
                                                           'relative_stock_delta': 10,
                                                           'absolute_stock_delta': 1,
                                                           'consider_end_contract_effect': True})
        wizard.execute()

    def process_orderpoints(self):
        """Function to call the scheduler without needing connector to work."""
        compute_wizard = self.env['procurement.order.compute.all'].create({
            'compute_all': False,
            'product_ids': [(4, self.test_product.id), (4, self.test_product3.id), (4, self.test_product4.id)],
        })
        self.env['procurement.order'].with_context(compute_product_ids=compute_wizard.product_ids.ids,
                                                   compute_all_products=compute_wizard.compute_all,
                                                   without_job=True)._procure_orderpoint_confirm()

    def test_01_procurement_jit_basic(self):
        procs = self.env['procurement.order'].search([('location_id', '=', self.location_b.id),
                                                      ('product_id', 'in', [self.test_product.id,
                                                                            self.test_product2.id,
                                                                            self.test_product3.id,
                                                                            self.test_product4.id,
                                                                            ])])
        self.assertFalse(procs)
        self.process_orderpoints()
        procs = self.env['procurement.order'].search([('location_id', '=', self.location_b.id),
                                                      ('product_id', 'in', [self.test_product.id,
                                                                            self.test_product2.id,
                                                                            self.test_product3.id,
                                                                            self.test_product4.id,
                                                                            ])], order='date_planned, product_id')

        self.assertEqual(len(procs), 8)

        self.assertEqual(procs[0].date_planned, "2015-03-15 10:00:00")
        self.assertEqual(procs[0].product_qty, 8)
        self.assertEqual(procs[0].state, 'running')
        self.assertEqual(procs[0].product_id, self.test_product)

        self.assertEqual(procs[1].date_planned, "2015-03-16 10:00:00")
        self.assertEqual(procs[1].product_qty, 8)
        self.assertEqual(procs[1].state, 'exception')
        self.assertEqual(procs[1].product_id, self.test_product3)

        self.assertEqual(procs[2].date_planned, "2015-03-20 10:00:00")
        self.assertEqual(procs[2].product_qty, 6)
        self.assertEqual(procs[2].state, 'running')
        self.assertEqual(procs[2].product_id, self.test_product)

        self.assertEqual(procs[3].date_planned, "2015-03-21 10:00:00")
        self.assertEqual(procs[3].product_qty, 6)
        self.assertEqual(procs[3].state, 'exception')
        self.assertEqual(procs[3].product_id, self.test_product3)

        self.assertEqual(procs[4].date_planned, "2015-03-25 10:00:00")
        self.assertEqual(procs[4].product_qty, 12)
        self.assertEqual(procs[4].state, 'running')
        self.assertEqual(procs[4].product_id, self.test_product)

        self.assertEqual(procs[5].date_planned, "2015-03-26 10:00:00")
        self.assertEqual(procs[5].product_qty, 12)
        self.assertEqual(procs[5].state, 'exception')
        self.assertEqual(procs[5].product_id, self.test_product3)

        self.assertEqual(procs[6].date_planned[:10], fields.Date.today())
        self.assertEqual(procs[6].product_qty, 6)
        self.assertEqual(procs[6].state, 'running')
        self.assertEqual(procs[6].product_id, self.test_product4)

        self.assertEqual(procs[7].date_planned[:10], fields.Date.today())
        self.assertEqual(procs[7].product_qty, 6)
        self.assertEqual(procs[7].state, 'running')
        self.assertEqual(procs[7].product_id, self.test_product4)

    def test_02_procurement_jit_delete_proc(self):
        """Check jit with deletion of confirmed procurement."""
        # Check that procurement_jit is not installed, otherwise this test is useless
        if self.env['ir.module.module'].search([('name', '=', 'procurement_jit'), ('state', '=', 'installed')]):
            self.skipTest("Procurement JIT module is installed")
        proc_env = self.env['procurement.order']
        proc_env.create({
            'name': "Procurement 1",
            'date_planned': '2015-03-19 18:00:00',
            'product_id': self.test_product.id,
            'product_qty': 5,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })
        proc_env.create({
            'name': "Procurement 3",
            'date_planned': '2015-03-19 18:00:00',
            'product_id': self.test_product3.id,
            'product_qty': 5,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })
        proc_env.create({
            'name': "Procurement 2",
            'date_planned': '2015-03-26 18:00:00',
            'product_id': self.test_product2.id,
            'product_qty': 5,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })

        self.process_orderpoints()
        procs = proc_env.search([('location_id', '=', self.location_b.id),
                                 ('product_id', 'in', [self.test_product.id,
                                                       self.test_product2.id,
                                                       self.test_product3.id])], order='date_planned, product_id')

        self.assertEqual(len(procs), 7)
        self.assertEqual(procs[0].product_id, self.test_product)
        self.assertEqual(procs[0].date_planned, "2015-03-15 10:00:00")
        self.assertEqual(procs[0].product_qty, 8)
        self.assertEqual(procs[0].state, 'running')

        self.assertEqual(procs[1].product_id, self.test_product3)
        self.assertEqual(procs[1].date_planned, "2015-03-16 10:00:00")
        self.assertEqual(procs[1].product_qty, 8)
        self.assertEqual(procs[1].state, 'exception')

        self.assertEqual(procs[2].product_id, self.test_product)
        self.assertEqual(procs[2].date_planned, "2015-03-20 10:00:00")
        self.assertEqual(procs[2].product_qty, 6)
        self.assertEqual(procs[2].state, 'running')

        self.assertEqual(procs[3].product_id, self.test_product3)
        self.assertEqual(procs[3].date_planned, "2015-03-21 10:00:00")
        self.assertEqual(procs[3].product_qty, 6)
        self.assertEqual(procs[3].state, 'exception')

        self.assertEqual(procs[4].product_id, self.test_product)
        self.assertEqual(procs[4].date_planned, "2015-03-25 10:00:00")
        self.assertEqual(procs[4].product_qty, 12)
        self.assertEqual(procs[4].state, 'running')

        self.assertEqual(procs[5].product_id, self.test_product3)
        self.assertEqual(procs[5].date_planned, "2015-03-26 10:00:00")
        self.assertEqual(procs[5].product_qty, 12)
        self.assertEqual(procs[5].state, 'exception')

        self.assertEqual(procs[6].product_id, self.test_product2)
        self.assertEqual(procs[6].date_planned, "2015-03-26 18:00:00")
        self.assertEqual(procs[6].product_qty, 5)
        self.assertEqual(procs[6].state, 'confirmed')

    def test_03_procurement_jit_several_procurements_deletion(self):
        """Check jit with several deletion of running procurements."""
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
        proc2 = proc_env.create({
            'name': "Procurement 3",
            'date_planned': '2015-03-27 00:00:00',
            'product_id': self.test_product3.id,
            'product_qty': 3,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })
        proc2.run()
        self.assertEqual(proc2.state, 'exception')
        proc3 = proc_env.create({
            'name': "Procurement 4",
            'date_planned': '2015-03-31 00:00:00',
            'product_id': self.test_product3.id,
            'product_qty': 3,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })
        proc3.run()
        self.assertEqual(proc3.state, 'exception')
        self.process_orderpoints()
        procs = proc_env.search([('location_id', '=', self.location_b.id),
                                 ('product_id', 'in', [self.test_product.id, self.test_product3.id])],
                                order='date_planned, product_id')

        # They should all be running
        self.assertEqual(len(procs), 6)
        self.assertEqual(procs[0].product_id, self.test_product)
        self.assertEqual(procs[0].date_planned, "2015-03-15 10:00:00")
        self.assertEqual(procs[0].product_qty, 8)
        self.assertEqual(procs[0].state, 'running')

        self.assertEqual(procs[1].product_id, self.test_product3)
        self.assertEqual(procs[1].date_planned, "2015-03-16 10:00:00")
        self.assertEqual(procs[1].product_qty, 8)
        self.assertEqual(procs[1].state, 'exception')

        self.assertEqual(procs[2].product_id, self.test_product)
        self.assertEqual(procs[2].date_planned, "2015-03-20 10:00:00")
        self.assertEqual(procs[2].product_qty, 6)
        self.assertEqual(procs[2].state, 'running')

        self.assertEqual(procs[3].product_id, self.test_product3)
        self.assertEqual(procs[3].date_planned, "2015-03-21 10:00:00")
        self.assertEqual(procs[3].product_qty, 6)
        self.assertEqual(procs[3].state, 'exception')

        self.assertEqual(procs[4].product_id, self.test_product)
        self.assertEqual(procs[4].date_planned, "2015-03-25 10:00:00")
        self.assertEqual(procs[4].product_qty, 12)
        self.assertEqual(procs[4].state, 'running')

        self.assertEqual(procs[5].product_id, self.test_product3)
        self.assertEqual(procs[5].date_planned, "2015-03-26 10:00:00")
        self.assertEqual(procs[5].product_qty, 12)
        self.assertEqual(procs[5].state, 'exception')

    def test_04_procurement_jit_with_fixed_in_moves(self):
        """Check jit with fixed incoming moves in the middle."""
        proc_env = self.env['procurement.order']
        proc_env.create({
            'name': "Procurement 1",
            'date_planned': '2015-03-23 00:00:00',
            'product_id': self.test_product.id,
            'product_qty': 8,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })
        proc_env.create({
            'name': "Procurement 2",
            'date_planned': '2015-03-24 00:00:00',
            'product_id': self.test_product3.id,
            'product_qty': 8,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })
        move1 = self.env["stock.move"].create({
            'name': "Incoming move 1",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 3,
            'location_id': self.location_inv.id,
            'location_dest_id': self.location_b.id,
            'date': "2015-03-19 12:00:00",
        })
        move1.action_confirm()
        move2 = self.env["stock.move"].create({
            'name': "Incoming move 2",
            'product_id': self.test_product3.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 3,
            'location_id': self.location_inv.id,
            'location_dest_id': self.location_b.id,
            'date': "2015-03-20 12:00:00",
        })
        move2.action_confirm()
        move3 = self.env["stock.move"].create({
            'name': "Incoming move 3",
            'product_id': self.test_product4.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 2,
            'location_id': self.location_inv.id,
            'location_dest_id': self.location_b.id,
            'date': "2015-03-20 12:00:00",
        })
        move3.action_confirm()
        self.process_orderpoints()
        procs = proc_env.search([('location_id', '=', self.location_b.id),
                                 ('product_id', 'in', [self.test_product.id, self.test_product3.id])],
                                order='date_planned, product_id')

        self.assertEqual(len(procs), 6)
        self.assertEqual(procs[0].date_planned, "2015-03-15 10:00:00")
        self.assertEqual(procs[0].product_qty, 8)
        self.assertEqual(procs[0].product_id, self.test_product)
        self.assertEqual(procs[0].state, 'running')

        self.assertEqual(procs[1].date_planned, "2015-03-16 10:00:00")
        self.assertEqual(procs[1].product_qty, 8)
        self.assertEqual(procs[1].product_id, self.test_product3)
        self.assertEqual(procs[1].state, 'exception')

        self.assertEqual(procs[2].date_planned, "2015-03-24 10:00:00")
        self.assertEqual(procs[2].product_qty, 6)
        self.assertEqual(procs[2].product_id, self.test_product)
        self.assertEqual(procs[2].state, 'running')

        self.assertEqual(procs[3].date_planned, "2015-03-24 10:00:00")
        self.assertEqual(procs[3].product_qty, 6)
        self.assertEqual(procs[3].product_id, self.test_product3)
        self.assertEqual(procs[3].state, 'exception')

        self.assertEqual(procs[4].date_planned, "2015-03-25 10:00:00")
        self.assertEqual(procs[4].product_qty, 10)
        self.assertEqual(procs[4].product_id, self.test_product)
        self.assertEqual(procs[4].state, 'running')

        self.assertEqual(procs[5].date_planned, "2015-03-26 10:00:00")
        self.assertEqual(procs[5].product_qty, 10)
        self.assertEqual(procs[5].product_id, self.test_product3)
        self.assertEqual(procs[5].state, 'exception')

        procs4 = proc_env.search([('location_id', '=', self.location_b.id),
                                  ('product_id', 'in', [self.test_product4.id])],
                                 order='date_planned, id')

        self.assertEqual(len(procs4), 2)
        self.assertEqual(procs4[0].product_qty, 4)
        self.assertEqual(procs4[1].product_qty, 6)

    def test_05_procurement_jit_oversupply(self):
        """Test redistribution of procurements when the location is over supplied."""
        proc_env = self.env['procurement.order']
        # First let's start with the basic procurement scenario
        self.test_01_procurement_jit_basic()
        move_need2 = self.browse_ref('stock_procurement_just_in_time.need2')
        move_need2.date = "2015-03-27 11:00:00"
        move_need7 = self.browse_ref('stock_procurement_just_in_time.need7')
        move_need7.date = "2015-03-28 11:00:00"
        # We create a new move in order to have a need at the end
        new_move = move_need2.copy({'date': "2015-03-30 11:10:00"})
        new_move.action_confirm()
        new_move2 = move_need7.copy({'date': "2015-03-31 11:10:00"})
        new_move2.action_confirm()
        self.process_orderpoints()
        procs = proc_env.search([('location_id', '=', self.location_b.id),
                                 ('product_id', 'in', [self.test_product.id, self.test_product3.id])],
                                order='date_planned, product_id')

        self.assertEqual(len(procs), 8)
        self.assertEqual(procs[0].date_planned, "2015-03-15 10:00:00")
        self.assertEqual(procs[0].product_qty, 8)
        self.assertEqual(procs[0].product_id, self.test_product)
        self.assertEqual(procs[0].state, 'running')

        self.assertEqual(procs[1].date_planned, "2015-03-16 10:00:00")
        self.assertEqual(procs[1].product_qty, 8)
        self.assertEqual(procs[1].product_id, self.test_product3)
        self.assertEqual(procs[1].state, 'exception')

        self.assertEqual(procs[2].date_planned, "2015-03-25 10:00:00")
        self.assertEqual(procs[2].product_qty, 12)
        self.assertEqual(procs[2].product_id, self.test_product)
        self.assertEqual(procs[2].state, 'running')

        self.assertEqual(procs[3].date_planned, "2015-03-26 10:00:00")
        self.assertEqual(procs[3].product_qty, 12)
        self.assertEqual(procs[3].product_id, self.test_product3)
        self.assertEqual(procs[3].state, 'exception')

        self.assertEqual(procs[4].date_planned, "2015-03-27 11:00:00")
        self.assertEqual(procs[4].product_qty, 6)
        self.assertEqual(procs[4].product_id, self.test_product)
        self.assertEqual(procs[4].state, 'running')

        self.assertEqual(procs[5].date_planned, "2015-03-28 11:00:00")
        self.assertEqual(procs[5].product_qty, 6)
        self.assertEqual(procs[5].product_id, self.test_product3)
        self.assertEqual(procs[5].state, 'exception')

        self.assertEqual(procs[6].date_planned, "2015-03-30 11:10:00")
        self.assertEqual(procs[6].product_qty, 6)
        self.assertEqual(procs[6].product_id, self.test_product)
        self.assertEqual(procs[6].state, 'running')

        self.assertEqual(procs[7].date_planned, "2015-03-31 11:10:00")
        self.assertEqual(procs[7].product_qty, 6)
        self.assertEqual(procs[7].product_id, self.test_product3)
        self.assertEqual(procs[7].state, 'exception')

    def test_06_procurement_jit_oversupply_from_zero(self):
        """Test redistribution of procurements with initial stock of zero."""
        proc_env = self.env['procurement.order']
        # First let's start with the basic procurement scenario
        self.test_01_procurement_jit_basic()

        procs = proc_env.search([('location_id', '=', self.location_b.id),
                                 ('product_id', 'in', [self.test_product.id, self.test_product3.id])],
                                order='date_planned, product_id')
        # Lets's make an oversupply with first procs and their moves if any (8 is not enough as it is max qty + 2)
        procs[0].product_qty = 10
        self.assertEqual(len(procs[0].move_ids), 1)
        procs[0].move_ids.product_uom_qty = 10
        procs[1].product_qty = 10

        move_need1 = self.browse_ref('stock_procurement_just_in_time.need1')
        move_need1.date = "2015-03-22 11:00:00"
        move_need6 = self.browse_ref('stock_procurement_just_in_time.need6')
        move_need6.date = "2015-03-23 11:00:00"

        self.process_orderpoints()
        procs = proc_env.search([('location_id', '=', self.location_b.id),
                                 ('product_id', 'in', [self.test_product.id, self.test_product3.id])],
                                order='date_planned, product_id')

        self.assertEqual(len(procs), 6)
        self.assertEqual(procs[0].date_planned, "2015-03-20 10:00:00")
        self.assertEqual(procs[0].product_qty, 6)
        self.assertEqual(procs[0].product_id, self.test_product)
        self.assertEqual(procs[0].state, 'running')

        self.assertEqual(procs[1].date_planned, "2015-03-20 10:00:00")
        self.assertEqual(procs[1].product_qty, 6)
        self.assertEqual(procs[1].product_id, self.test_product)
        self.assertEqual(procs[1].state, 'running')

        self.assertEqual(procs[2].date_planned, "2015-03-21 10:00:00")
        self.assertEqual(procs[2].product_qty, 6)
        self.assertEqual(procs[2].product_id, self.test_product3)
        self.assertEqual(procs[2].state, 'exception')

        self.assertEqual(procs[3].date_planned, "2015-03-21 10:00:00")
        self.assertEqual(procs[3].product_qty, 6)
        self.assertEqual(procs[3].product_id, self.test_product3)
        self.assertEqual(procs[3].state, 'exception')

        self.assertEqual(procs[4].date_planned, "2015-03-25 10:00:00")
        self.assertEqual(procs[4].product_qty, 12)
        self.assertEqual(procs[4].product_id, self.test_product)
        self.assertEqual(procs[4].state, 'running')

        self.assertEqual(procs[5].date_planned, "2015-03-26 10:00:00")
        self.assertEqual(procs[5].product_qty, 12)
        self.assertEqual(procs[5].product_id, self.test_product3)
        self.assertEqual(procs[5].state, 'exception')

    def test_07_procurement_jit_with_initial_stock(self):
        """Test that scheduling works correctly with an initial stock."""
        self.env['stock.quant'].create({
            'product_id': self.test_product.id,
            'location_id': self.location_b.id,
            'qty': 5,
        })
        procs = self.env['procurement.order'].search([('location_id', '=', self.location_b.id),
                                                      ('product_id', 'in', [self.test_product.id,
                                                                            self.test_product2.id,
                                                                            self.test_product3.id,
                                                                            self.test_product4.id,
                                                                            ])])
        self.assertFalse(procs)
        self.process_orderpoints()
        procs = self.env['procurement.order'].search([('location_id', '=', self.location_b.id),
                                                      ('product_id', 'in', [self.test_product.id])],
                                                     order='date_planned, product_id')

        self.assertEqual(len(procs), 2)

        self.assertEqual(procs[0].date_planned, "2015-03-20 10:00:00")
        self.assertEqual(procs[0].product_qty, 8)
        self.assertEqual(procs[0].state, 'running')
        self.assertEqual(procs[0].product_id, self.test_product)

        self.assertEqual(procs[1].date_planned, "2015-03-25 10:00:00")
        self.assertEqual(procs[1].product_qty, 14)
        self.assertEqual(procs[1].state, 'running')
        self.assertEqual(procs[1].product_id, self.test_product)

    def test_08_procurement_jit_with_initial_stock_over_max(self):
        """Test that scheduling works correctly with an initial stock over max value."""
        self.env['stock.quant'].create({
            'product_id': self.test_product.id,
            'location_id': self.location_b.id,
            'qty': 15,
        })
        procs = self.env['procurement.order'].search([('location_id', '=', self.location_b.id),
                                                      ('product_id', 'in', [self.test_product.id,
                                                                            self.test_product2.id,
                                                                            self.test_product3.id,
                                                                            self.test_product4.id,
                                                                            ])])
        self.assertFalse(procs)
        self.process_orderpoints()
        procs = self.env['procurement.order'].search([('location_id', '=', self.location_b.id),
                                                      ('product_id', 'in', [self.test_product.id])],
                                                     order='date_planned, product_id')

        self.assertEqual(len(procs), 1)

        self.assertEqual(procs[0].date_planned, "2015-03-25 10:00:00")
        self.assertEqual(procs[0].product_qty, 12)
        self.assertEqual(procs[0].state, 'running')
        self.assertEqual(procs[0].product_id, self.test_product)

    def test_09_procurement_jit_removal(self):
        """Test removal of unecessary procurements at the end."""
        proc_env = self.env['procurement.order']
        # First let's start with the basic procurement scenario
        self.test_01_procurement_jit_basic()
        move_need2 = self.browse_ref('stock_procurement_just_in_time.need2')
        move_need2.action_cancel()
        move_need7 = self.browse_ref('stock_procurement_just_in_time.need7')
        move_need7.action_cancel()
        self.process_orderpoints()
        procs = proc_env.search([('location_id', '=', self.location_b.id),
                                 ('product_id', 'in', [self.test_product.id, self.test_product3.id])],
                                order='date_planned, product_id')

        self.assertEqual(len(procs), 4)

        self.assertEqual(procs[0].date_planned, "2015-03-15 10:00:00")
        self.assertEqual(procs[0].product_qty, 8)
        self.assertEqual(procs[0].product_id, self.test_product)
        self.assertEqual(procs[0].state, 'running')

        self.assertEqual(procs[1].date_planned, "2015-03-16 10:00:00")
        self.assertEqual(procs[1].product_qty, 8)
        self.assertEqual(procs[1].product_id, self.test_product3)
        self.assertEqual(procs[1].state, 'exception')

        self.assertEqual(procs[2].date_planned, "2015-03-25 10:00:00")
        self.assertEqual(procs[2].product_qty, 12)
        self.assertEqual(procs[2].product_id, self.test_product)
        self.assertEqual(procs[2].state, 'running')

        self.assertEqual(procs[3].date_planned, "2015-03-26 10:00:00")
        self.assertEqual(procs[3].product_qty, 12)
        self.assertEqual(procs[3].product_id, self.test_product3)
        self.assertEqual(procs[3].state, 'exception')

    def test_01_unlink_moves_of_partially_done_chain(self):
        # Let's add rules to deal with chains
        procurement_rule_a_to_b = self.browse_ref('stock_procurement_just_in_time.procurement_rule_a_to_b')
        procurement_rule_a_to_b.procure_method = 'make_to_order'

        rule_orig_to_a = self.env['procurement.rule'].create({
            'name': "Orig = > A(MTO)",
            'action': 'move',
            'location_id': self.location_a.id,
            'location_src_id': self.stock_location_orig.id,
            'warehouse_id': self.browse_ref('stock.warehouse0').id,
            'route_id': self.browse_ref('stock_procurement_just_in_time.test_route').id,
            'group_propagation_option': 'propagate',
            'propagate': True,
            'picking_type_id': self.browse_ref('stock.picking_type_internal').id,
            'procure_method': 'make_to_stock',
            'delay': 5,
        })

        # First let's start with the basic procurement scenario
        procs = self.env['procurement.order'].search([('location_id', '=', self.location_b.id),
                                                      ('product_id', 'in', [self.test_product.id])])
        self.assertFalse(procs)
        self.process_orderpoints()
        procs = self.env['procurement.order'].search([('location_id', '=', self.location_b.id),
                                                      ('product_id', 'in', [self.test_product.id])],
                                                     order='date_planned, product_id')

        self.assertEqual(len(procs), 3)

        self.assertEqual(procs[0].date_planned, "2015-03-15 10:00:00")
        self.assertEqual(procs[0].product_qty, 8)
        self.assertEqual(procs[0].state, 'running')
        self.assertEqual(procs[0].product_id, self.test_product)

        self.assertEqual(procs[1].date_planned, "2015-03-20 10:00:00")
        self.assertEqual(procs[1].product_qty, 6)
        self.assertEqual(procs[1].state, 'running')
        self.assertEqual(procs[1].product_id, self.test_product)

        self.assertEqual(procs[2].date_planned, "2015-03-25 10:00:00")
        self.assertEqual(procs[2].product_qty, 12)
        self.assertEqual(procs[2].state, 'running')
        self.assertEqual(procs[2].product_id, self.test_product)

        proc_to_be_removed = procs[1]
        proc_to_be_removed_id = proc_to_be_removed.id

        # Let's create a supply chain for move of proc_to_be_removed and receive 2 units for proc_to_be_removed.
        move_to_b = proc_to_be_removed.move_ids
        self.assertEqual(len(move_to_b), 1)
        self.assertTrue(move_to_b.picking_id)

        proc_in_a = self.env['procurement.order'].search([('location_id', '=', self.location_a.id),
                                                          ('product_id', '=', self.test_product.id),
                                                          ('product_qty', '=', 6),
                                                          ('move_dest_id', '=', move_to_b.id)])
        self.assertEqual(len(proc_in_a), 1)
        proc_in_a.run()
        self.assertEqual(proc_in_a.rule_id, rule_orig_to_a)
        move_to_a = proc_in_a.move_ids
        self.assertEqual(len(move_to_a), 1)

        move_to_a.force_assign()
        self.assertTrue(move_to_a.picking_id)

        wizard_id = move_to_a.picking_id.do_enter_transfer_details()['res_id']
        wizard = self.env['stock.transfer_details'].browse(wizard_id)
        self.assertEqual(len(wizard.item_ids), 1)
        self.assertEqual(wizard.item_ids.product_id, self.test_product)
        self.assertEqual(wizard.item_ids.quantity, 6)
        wizard.item_ids.quantity = 2
        wizard.do_detailed_transfer()

        move_to_a_2 = self.env['stock.move'].search([('split_from', '=', move_to_a.id)])
        self.assertEqual(len(move_to_a_2), 1)
        self.assertEqual(move_to_a.product_uom_qty, 2)
        self.assertEqual(move_to_a.state, 'done')
        self.assertEqual(move_to_a.procurement_id.state, 'done')
        self.assertEqual(move_to_a.procurement_id.product_qty, 2)
        self.assertEqual(move_to_a_2.product_uom_qty, 4)
        self.assertEqual(move_to_a_2.state, 'confirmed')
        self.assertEqual(move_to_a_2.procurement_id.state, 'running')
        self.assertEqual(move_to_a_2.procurement_id.product_qty, 4)

        move_to_b_2 = self.env['stock.move'].search([('split_from', '=', move_to_b.id)])
        self.assertEqual(move_to_a_2.move_dest_id, move_to_b_2)
        self.assertEqual(move_to_a_2.procurement_id.move_dest_id, move_to_b_2)
        self.assertEqual(move_to_b_2.state, 'waiting')
        self.assertEqual(move_to_b_2.product_qty, 4)
        self.assertEqual(move_to_b_2.procurement_id.state, 'running')
        self.assertEqual(move_to_b_2.procurement_id.product_qty, 4)

        ids_to_be_removed = [move_to_a_2.id, move_to_b.id]
        ids_not_to_be_removed = [move_to_a.id]

        # Let's reschedule
        move_need2 = self.browse_ref('stock_procurement_just_in_time.need2')
        move_need2.action_cancel()
        move_need7 = self.browse_ref('stock_procurement_just_in_time.need7')
        move_need7.action_cancel()
        self.process_orderpoints()
        procs = self.env['procurement.order'].search([('location_id', '=', self.location_b.id),
                                                      ('product_id', 'in', [self.test_product.id,
                                                                            self.test_product3.id])],
                                                     order='date_planned, product_id')
        self.assertEqual(len(procs), 4)

        self.assertEqual(procs[0].date_planned, "2015-03-15 10:00:00")
        self.assertEqual(procs[0].product_qty, 8)
        self.assertEqual(procs[0].product_id, self.test_product)
        self.assertEqual(procs[0].state, 'running')

        self.assertEqual(procs[1].date_planned, "2015-03-16 10:00:00")
        self.assertEqual(procs[1].product_qty, 8)
        self.assertEqual(procs[1].product_id, self.test_product3)
        self.assertEqual(procs[1].state, 'exception')

        self.assertEqual(procs[2].date_planned, "2015-03-25 10:00:00")
        self.assertEqual(procs[2].product_qty, 12)
        self.assertEqual(procs[2].product_id, self.test_product)
        self.assertEqual(procs[2].state, 'running')

        self.assertEqual(procs[3].date_planned, "2015-03-26 10:00:00")
        self.assertEqual(procs[3].product_qty, 12)
        self.assertEqual(procs[3].product_id, self.test_product3)
        self.assertEqual(procs[3].state, 'exception')

        # Let's check procurements/moves deletion
        self.assertEqual(proc_in_a.product_qty, 2)
        for move_id in ids_to_be_removed:
            self.assertNotIn(move_id, self.env['stock.move'].search([]).ids)
        for move_id in ids_not_to_be_removed:
            self.assertIn(move_id, self.env['stock.move'].search([]).ids)
        self.assertNotIn(proc_to_be_removed_id, self.env['procurement.order'].search([]).ids)

    def test_12_procurement_jit(self):
        """
        Cancelling procurement of a move which parent is done.
        """

        proc1 = self.env['procurement.order'].create({
            'name': "Test procurement",
            'product_id': self.test_product.id,
            'product_qty': 1,
            'product_uom': self.unit.id,
            'location_id': self.customer.id,
            'rule_id': self.rule_move.id,
        })
        proc1.run()
        move_dest = self.env['stock.move'].create({
            'name': "Move dest",
            'product_id': self.test_product.id,
            'product_uom_qty': 1,
            'product_uom': self.unit.id,
            'location_id': self.stock.id,
            'location_dest_id': self.customer.id,
            'procurement_id': proc1.id,
            'propagate': True,
        })
        move_dest.action_confirm()
        self.assertEqual(move_dest.state, 'confirmed')
        move_parent = self.env['stock.move'].create({
            'name': "Move parent",
            'product_id': self.test_product.id,
            'product_uom_qty': 1,
            'product_uom': self.unit.id,
            'location_id': self.supplier.id,
            'location_dest_id': self.stock.id,
            'move_dest_id': move_dest.id,
            'propagate': True,
        })
        move_parent.action_confirm()
        self.assertEqual(move_parent.state, 'confirmed')

        move_parent.action_done()
        self.assertEqual(move_parent.state, 'done')
        self.assertEqual(move_dest.state, 'assigned')
        proc1.with_context(cancel_procurement=True).cancel()
        self.assertEqual(proc1.state, 'cancel')
        self.assertEqual(move_dest.state, 'cancel')

    def test_13_procurement_jit(self):
        """
        Cancelling a procurement with several moves and one of them is done.
        """

        proc1 = self.env['procurement.order'].create({
            'name': "Test procurement",
            'product_id': self.test_product.id,
            'product_qty': 5,
            'product_uos_qty': 5,
            'product_uom': self.unit.id,
            'location_id': self.customer.id,
            'rule_id': self.rule_move.id,
        })

        proc1.run()
        move1 = self.env['stock.move'].create({
            'name': "Move dest",
            'product_id': self.test_product.id,
            'product_uom_qty': 2,
            'product_uom': self.unit.id,
            'location_id': self.stock.id,
            'location_dest_id': self.customer.id,
            'procurement_id': proc1.id,
            'propagate': True,
        })
        move1.action_confirm()
        self.assertEqual(move1.state, 'confirmed')
        move2 = self.env['stock.move'].create({
            'name': "Move parent",
            'product_id': self.test_product.id,
            'product_uom_qty': 3,
            'product_uom': self.unit.id,
            'location_id': self.stock.id,
            'location_dest_id': self.customer.id,
            'procurement_id': proc1.id,
            'propagate': True,
        })
        move2.action_confirm()
        self.assertEqual(move2.state, 'confirmed')

        move2.action_done()
        self.assertEqual(move2.state, 'done')
        self.assertEqual(move1.state, 'confirmed')
        proc1.cancel()
        self.assertEqual(proc1.state, 'cancel')
        self.assertEqual(proc1.product_qty, 3)
        self.assertEqual(proc1.product_uos_qty, 3)
        self.assertEqual(move2.state, 'done')
        self.assertEqual(move1.state, 'cancel')
    
    def test_14_procurement_jit_duration_end_contract(self):
        """Check jit with deletion of confirmed procurement."""
        # Check that procurement_jit is not installed, otherwise this test is useless
        if self.env['ir.module.module'].search([('name', '=', 'procurement_jit'), ('state', '=', 'installed')]):
            self.skipTest("Procurement JIT module is installed")

        self.warehouse_orderpoint1.fill_strategy = 'duration'
        self.warehouse_orderpoint1.fill_duration = 4

        proc_env = self.env['procurement.order']
        proc_env.create({
            'name': "Procurement 1",
            'date_planned': '2015-03-19 18:00:00',
            'product_id': self.test_product.id,
            'product_qty': 21,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })
        proc_env.create({
            'name': "Procurement 3",
            'date_planned': '2015-03-19 18:00:00',
            'product_id': self.test_product3.id,
            'product_qty': 5,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })
        proc_env.create({
            'name': "Procurement 2",
            'date_planned': '2015-03-26 18:00:00',
            'product_id': self.test_product2.id,
            'product_qty': 5,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })

        self.process_orderpoints()
        procs = proc_env.search([('location_id', '=', self.location_b.id),
                                 ('product_id', 'in', [self.test_product.id,
                                                       self.test_product2.id,
                                                       self.test_product3.id])], order='date_planned, product_id')

        self.assertEqual(len(procs), 7)
        self.assertEqual(procs[0].product_id, self.test_product)
        self.assertEqual(procs[0].date_planned, "2015-03-15 10:00:00")
        self.assertEqual(procs[0].product_qty, 8)
        self.assertEqual(procs[0].state, 'running')

        self.assertEqual(procs[1].product_id, self.test_product3)
        self.assertEqual(procs[1].date_planned, "2015-03-16 10:00:00")
        self.assertEqual(procs[1].product_qty, 8)
        self.assertEqual(procs[1].state, 'exception')

        self.assertEqual(procs[2].product_id, self.test_product)
        self.assertEqual(procs[2].date_planned, "2015-03-20 10:00:00")
        self.assertEqual(procs[2].product_qty, 12)
        self.assertEqual(procs[2].state, 'running')

        self.assertEqual(procs[3].product_id, self.test_product3)
        self.assertEqual(procs[3].date_planned, "2015-03-21 10:00:00")
        self.assertEqual(procs[3].product_qty, 6)
        self.assertEqual(procs[3].state, 'exception')

        self.assertEqual(procs[4].product_id, self.test_product)
        self.assertEqual(procs[4].date_planned, "2015-03-25 10:00:00")
        self.assertEqual(procs[4].product_qty, 2)
        self.assertEqual(procs[4].state, 'running')

        self.assertEqual(procs[5].product_id, self.test_product3)
        self.assertEqual(procs[5].date_planned, "2015-03-26 10:00:00")
        self.assertEqual(procs[5].product_qty, 12)
        self.assertEqual(procs[5].state, 'exception')

        self.assertEqual(procs[6].product_id, self.test_product2)
        self.assertEqual(procs[6].date_planned, "2015-03-26 18:00:00")
        self.assertEqual(procs[6].product_qty, 5)
        self.assertEqual(procs[6].state, 'confirmed')

    def test_15_procurement_jit_duration_no_end_contract(self):
        """Check jit with deletion of confirmed procurement."""
        # Check that procurement_jit is not installed, otherwise this test is useless
        if self.env['ir.module.module'].search([('name', '=', 'procurement_jit'), ('state', '=', 'installed')]):
            self.skipTest("Procurement JIT module is installed")

        self.warehouse_orderpoint1.fill_strategy = 'duration'
        self.warehouse_orderpoint1.fill_duration = 4
        wizard = self.env['stock.config.settings'].create({'delete_moves_cancelled_by_planned': True,
                                                           'relative_stock_delta': 10,
                                                           'absolute_stock_delta': 2,
                                                           'consider_end_contract_effect': False})
        wizard.execute()

        proc_env = self.env['procurement.order']
        proc_env.create({
            'name': "Procurement 1",
            'date_planned': '2015-03-19 18:00:00',
            'product_id': self.test_product.id,
            'product_qty': 21,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })
        proc_env.create({
            'name': "Procurement 3",
            'date_planned': '2015-03-19 18:00:00',
            'product_id': self.test_product3.id,
            'product_qty': 5,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })
        proc_env.create({
            'name': "Procurement 2",
            'date_planned': '2015-03-26 18:00:00',
            'product_id': self.test_product2.id,
            'product_qty': 5,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })

        self.process_orderpoints()
        procs = proc_env.search([('location_id', '=', self.location_b.id),
                                 ('product_id', 'in', [self.test_product.id,
                                                       self.test_product2.id,
                                                       self.test_product3.id])], order='date_planned, product_id')

        self.assertEqual(len(procs), 6)
        self.assertEqual(procs[0].product_id, self.test_product)
        self.assertEqual(procs[0].date_planned, "2015-03-15 10:00:00")
        self.assertEqual(procs[0].product_qty, 10)
        self.assertEqual(procs[0].state, 'running')

        self.assertEqual(procs[1].product_id, self.test_product3)
        self.assertEqual(procs[1].date_planned, "2015-03-16 10:00:00")
        self.assertEqual(procs[1].product_qty, 8)
        self.assertEqual(procs[1].state, 'exception')

        self.assertEqual(procs[2].product_id, self.test_product3)
        self.assertEqual(procs[2].date_planned, "2015-03-21 10:00:00")
        self.assertEqual(procs[2].product_qty, 6)
        self.assertEqual(procs[2].state, 'exception')

        self.assertEqual(procs[3].product_id, self.test_product)
        self.assertEqual(procs[3].date_planned, "2015-03-24 10:00:00")
        self.assertEqual(procs[3].product_qty, 12)
        self.assertEqual(procs[3].state, 'running')

        self.assertEqual(procs[4].product_id, self.test_product3)
        self.assertEqual(procs[4].date_planned, "2015-03-26 10:00:00")
        self.assertEqual(procs[4].product_qty, 12)
        self.assertEqual(procs[4].state, 'exception')

        self.assertEqual(procs[5].product_id, self.test_product2)
        self.assertEqual(procs[5].date_planned, "2015-03-26 18:00:00")
        self.assertEqual(procs[5].product_qty, 5)
        self.assertEqual(procs[5].state, 'confirmed')
