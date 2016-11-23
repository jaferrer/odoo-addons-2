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


class TestPurchaseGroupByPeriod(common.TransactionCase):
    def setUp(self):
        super(TestPurchaseGroupByPeriod, self).setUp()
        self.product_a1232 = self.browse_ref("product.product_product_6")
        self.product_a1232.route_ids = [(4, self.ref("purchase.route_warehouse0_buy"))]
        self.supplier = self.browse_ref("base.res_partner_1")
        self.stock = self.browse_ref("stock.stock_location_stock")
        self.product_uom_unit_id = self.ref("product.product_uom_unit")
        self.period_fortnight = self.browse_ref("purchase_procurement_just_in_time.fortnight")
        self.period_month = self.browse_ref("purchase_procurement_just_in_time.month")
        self.period_year = self.browse_ref("purchase_procurement_just_in_time.year")
        draft_order_ids = self.env['purchase.order'].search([('state', '=', 'draft'),
                                                             ('partner_id', '=', self.supplier.id)])
        draft_order_ids.unlink()

        # def test_10_all_by_fortnight(self):
        #     """Full test of the grouping function by fortnight."""
        #     # First procurement
        #     self.supplier.order_group_period = self.period_fortnight
        #     proc1 = self.env['procurement.order'].create({
        #         'name': 'Test Procurement 1',
        #         'date_planned': '2015-02-09 15:37:00',
        #         'product_id': self.product_a1232.id,
        #         'product_qty': 11,
        #         'product_uom': self.product_uom_unit_id,
        #         'warehouse_id': self.ref('stock.warehouse0'),
        #         'location_id': self.stock.id,
        #     })
        #     proc1.run()
        #     proc1.check()
        #     self.assertTrue(proc1.purchase_id)
        #     order1_id = proc1.purchase_id
        #     self.assertEqual(order1_id.date_order[0:10], "2015-01-26")
        #     self.assertEqual(order1_id._test_compute_date_order_max()[0:10], "2015-02-08")
        #     # Second procurement inside time frame
        #     proc2 = self.env['procurement.order'].create({
        #         'name': 'Test Procurement 2',
        #         'date_planned': '2015-02-12 18:56:00',
        #         'product_id': self.product_a1232.id,
        #         'product_qty': 12,
        #         'product_uom': self.product_uom_unit_id,
        #         'warehouse_id': self.ref('stock.warehouse0'),
        #         'location_id': self.stock.id,
        #     })
        #     proc2.run()
        #     proc2.check()
        #     self.assertEqual(proc2.purchase_id, order1_id)
        #     # Third procurement outside time frame on first day
        #     proc3 = self.env['procurement.order'].create({
        #         'name': 'Test Procurement 3',
        #         'date_planned': '2015-03-13 18:56:00',
        #         'product_id': self.product_a1232.id,
        #         'product_qty': 13,
        #         'product_uom': self.product_uom_unit_id,
        #         'warehouse_id': self.ref('stock.warehouse0'),
        #         'location_id': self.stock.id,
        #     })
        #     proc3.run()
        #     proc3.check()
        #     self.assertTrue(proc3.purchase_id)
        #     order3_id = proc3.purchase_id
        #     print 'order3_id', order3_id
        #     self.assertEqual(order3_id.date_order[0:10], "2015-03-09")
        #     self.assertEqual(order3_id._test_compute_date_order_max()[0:10], "2015-03-22")
        #     # Fourth procurement inside time frame of proc3 (last day)
        #     proc4 = self.env['procurement.order'].create({
        #         'name': 'Test Procurement 4',
        #         'date_planned': '2015-03-26 21:46:00',
        #         'product_id': self.product_a1232.id,
        #         'product_qty': 14,
        #         'product_uom': self.product_uom_unit_id,
        #         'warehouse_id': self.ref('stock.warehouse0'),
        #         'location_id': self.stock.id,
        #     })
        #     proc4.run()
        #     proc4.check()
        #     self.assertEqual(proc4.purchase_id, order3_id)
        #
        # def test_20_group_by_days(self):
        #     """Check grouping by days."""
        #     tf = self.env['procurement.time.frame'].create({
        #         'name': "3 days",
        #         'nb': 3,
        #         'period_type': 'days'
        #     })
        #     self.supplier.order_group_period = tf
        #     proc1 = self.env['procurement.order'].create({
        #         'name': 'Test Procurement 1',
        #         'date_planned': '2015-02-11 07:12:00',
        #         'product_id': self.product_a1232.id,
        #         'product_qty': 21,
        #         'product_uom': self.product_uom_unit_id,
        #         'warehouse_id': self.ref('stock.warehouse0'),
        #         'location_id': self.stock.id,
        #     })
        #     proc1.run()
        #     proc1.check()
        #     self.assertTrue(proc1.purchase_id)
        #     order1_id = proc1.purchase_id
        #     self.assertEqual(order1_id.date_order[0:10], "2015-02-06")
        #     self.assertEqual(order1_id._test_compute_date_order_max()[0:10], "2015-02-08")
        #
        # def test_30_group_by_months(self):
        #     """Check grouping by months."""
        #     tf = self.env['procurement.time.frame'].create({
        #         'name': "Quarter",
        #         'nb': 3,
        #         'period_type': 'months'
        #     })
        #     self.supplier.order_group_period = tf
        #     proc1 = self.env['procurement.order'].create({
        #         'name': 'Test Procurement 1',
        #         'date_planned': '2015-07-10 11:07:00',
        #         'product_id': self.product_a1232.id,
        #         'product_qty': 21,
        #         'product_uom': self.product_uom_unit_id,
        #         'warehouse_id': self.ref('stock.warehouse0'),
        #         'location_id': self.stock.id,
        #     })
        #     proc1.run()
        #     proc1.check()
        #     self.assertTrue(proc1.purchase_id)
        #     order1_id = proc1.purchase_id
        #     self.assertEqual(order1_id.date_order[0:10], "2015-07-01")
        #     self.assertEqual(order1_id._test_compute_date_order_max()[0:10], "2015-09-30")
        #
        # def test_40_group_by_years(self):
        #     """Check grouping by years."""
        #     tf = self.env['procurement.time.frame'].create({
        #         'name': "Two years",
        #         'nb': 2,
        #         'period_type': 'years'
        #     })
        #     self.supplier.order_group_period = tf
        #     proc1 = self.env['procurement.order'].create({
        #         'name': 'Test Procurement 1',
        #         'date_planned': '2015-09-24 11:07:00',
        #         'product_id': self.product_a1232.id,
        #         'product_qty': 21,
        #         'product_uom': self.product_uom_unit_id,
        #         'warehouse_id': self.ref('stock.warehouse0'),
        #         'location_id': self.stock.id,
        #     })
        #     proc1.run()
        #     proc1.check()
        #     self.assertTrue(proc1.purchase_id)
        #     order1_id = proc1.purchase_id
        #     self.assertEqual(order1_id.date_order[0:10], "2015-01-01")
        #     self.assertEqual(order1_id._test_compute_date_order_max()[0:10], "2016-12-31")
