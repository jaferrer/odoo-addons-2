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
        self.supplier1.order_group_period = self.browse_ref('purchase_group_by_period.week')
        self.product1 = self.browse_ref('purchase_procurement_just_in_time.product1')
        self.product2 = self.browse_ref('purchase_procurement_just_in_time.product2')
        self.supplierinfo1 = self.browse_ref('purchase_procurement_just_in_time.supplierinfo1')
        self.supplierinfo1.delay = 2

    def create_procurement_order_1(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 1 (Purchase Scheduler Sweeper)',
            'product_id': self.product1.id,
            'product_qty': 7,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock.stock_location_stock'),
            'date_planned': '2016-02-05 15:00:00',
            'product_uom': self.ref('product.product_uom_unit'),
        })

    def create_procurement_order_2(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 2 (Purchase Scheduler Sweeper)',
            'product_id': self.product1.id,
            'product_qty': 40,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock.stock_location_stock'),
            'date_planned': '2016-02-12 15:00:00',
            'product_uom': self.ref('product.product_uom_unit'),
        })

    def test_10_sweep_purchase_order(self):
        """
        Testing calculation of opmsg_reduce_qty, to_delete and remaining_qty
        """

        procurement_order_1 = self.create_procurement_order_1()
        procurement_order_1.run()
        self.assertTrue(procurement_order_1.rule_id.action == 'buy')
        self.assertTrue(procurement_order_1.purchase_line_id)
        procurement_order_2 = self.create_procurement_order_2()
        procurement_order_2.run()
        self.assertTrue(procurement_order_2.rule_id.action == 'buy')
        purchase_order_1 = procurement_order_1.purchase_id
        purchase_order_2 = procurement_order_2.purchase_id
        self.assertNotEqual(purchase_order_1, purchase_order_2)

        procurement_order_2.date_planned = '2016-02-04 15:00:00'
        procurement_order_2.action_reschedule()

        purchases = purchase_order_1 + purchase_order_2
        purchases.sweep()
        purchase_order_1 = procurement_order_1.purchase_id
        purchase_order_2 = procurement_order_2.purchase_id
        self.assertEqual(purchase_order_1, purchase_order_2)
