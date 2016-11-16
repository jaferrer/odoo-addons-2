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


class TestPurchaseMergeOrderLines(common.TransactionCase):

    def setUp(self):
        super(TestPurchaseMergeOrderLines, self).setUp()
        self.product = self.browse_ref('purchase_merge_order_lines.test_product')
        self.incoterm1 = self.browse_ref('stock.incoterm_EXW')
        self.incoterm2 = self.browse_ref('stock.incoterm_FCA')
        self.payment_term_1 = self.browse_ref('account.account_payment_term_15days')
        self.payment_term_2 = self.browse_ref('account.account_payment_term')
        self.stock = self.browse_ref('stock.stock_location_stock')
        self.buy_rule = self.browse_ref('purchase_merge_order_lines.buy_rule')
        self.supplierinfo = self.browse_ref('purchase_merge_order_lines.supplierinfo')

    def create_procurement_order_1(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 5 (Sirail Achats)',
            'product_id': self.product.id,
            'product_qty': 80,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.stock.id,
            'date_planned': '3003-02-08 14:37:00',
            'product_uom': self.ref('product.product_uom_unit'),
            'rule_id': self.buy_rule.id
        })

    def create_procurement_order_2(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 6 (Sirail Achats)',
            'product_id': self.product.id,
            'product_qty': 80,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.stock.id,
            'date_planned': '3002-02-08 14:37:00',
            'product_uom': self.ref('product.product_uom_unit'),
            'rule_id': self.buy_rule.id
        })

    def create_procurement_order_3(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 5 (Sirail Achats)',
            'product_id': self.product.id,
            'product_qty': 80,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.stock.id,
            'date_planned': '3003-02-08 14:37:00',
            'product_uom': self.ref('product.product_uom_unit'),
            'rule_id': self.buy_rule.id
        })

    def create_procurement_order_4(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 6 (Sirail Achats)',
            'product_id': self.product.id,
            'product_qty': 50,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.stock.id,
            'date_planned': '3002-02-08 14:37:00',
            'product_uom': self.ref('product.product_uom_unit'),
            'rule_id': self.buy_rule.id
        })

    def create_procurement_order_5(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 5 (Sirail Achats)',
            'product_id': self.product.id,
            'product_qty': 30,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.stock.id,
            'date_planned': '3003-02-08 14:37:00',
            'product_uom': self.ref('product.product_uom_unit'),
            'rule_id': self.buy_rule.id
        })

    def create_procurement_order_6(self):
        return self.env['procurement.order'].create({
            'name': 'Procurement order 6 (Sirail Achats)',
            'product_id': self.product.id,
            'product_qty': 50,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.stock.id,
            'date_planned': '3002-02-08 14:37:00',
            'product_uom': self.ref('product.product_uom_unit'),
            'rule_id': self.buy_rule.id
        })

    def test_10_purchase_merge_order_lines(self):

        """
        Test with two procurements of same quantities
        """

        procurement1 = self.create_procurement_order_1()
        procurement2 = self.create_procurement_order_2()

        self.assertFalse(procurement1.purchase_line_id)
        self.assertFalse(procurement1.purchase_id)
        self.assertFalse(procurement2.purchase_line_id)
        self.assertFalse(procurement2.purchase_id)
        procurement1.run()
        self.assertEqual(procurement1.state, 'buy_to_run')
        procurement2.run()
        self.assertEqual(procurement2.state, 'buy_to_run')

        self.env['procurement.order'].purchase_schedule(compute_all_products=False, compute_product_ids=self.product,
                                                        jobify=False)

        self.assertTrue(procurement1.purchase_id)
        self.assertTrue(procurement1.purchase_line_id)
        order1 = procurement1.purchase_line_id.order_id
        self.assertEqual(order1, procurement1.purchase_id)
        self.assertTrue(procurement2.purchase_line_id)
        order2 = procurement2.purchase_line_id.order_id
        self.assertNotEqual(order1, order2)
        self.assertEqual(len(order1.order_line), 1)
        self.assertEqual(order1.order_line.product_qty, 100)
        self.assertEqual(len(order2.order_line), 1)
        self.assertEqual(order2.order_line.product_qty, 100)
        self.assertEqual(order2, procurement2.purchase_id)

        self.assertEqual(order1.state, 'draft')
        self.assertEqual(order2.state, 'draft')
        order1.write({'incoterm_id': self.incoterm1.id, 'payment_term_id': self.payment_term_1.id})
        order2.write({'incoterm_id': self.incoterm2.id, 'payment_term_id': self.payment_term_2.id})
        self.assertGreater(order1.date_order, order2.date_order)

        result = order1.search([('id', 'in', [order1.id, order2.id])]). \
            with_context(merge_different_dates=True).do_merge()

        list_keys = result.keys()
        self.assertEqual(len(list_keys), 1)
        merged_order_id = list_keys[0]
        lst = result.get(merged_order_id)
        self.assertEqual(len(lst), 2)
        self.assertIn(order1.id, lst)
        self.assertIn(order2.id, lst)
        merged_order = order1.search([('id', '=', merged_order_id)])

        self.assertEqual(len(merged_order), 1)
        self.assertEqual(len(merged_order.order_line), 1)
        self.assertEqual(merged_order.order_line.product_qty, 160)
        self.assertEqual(len(merged_order.order_line.procurement_ids), 2)
        self.assertIn(procurement1, merged_order.order_line.procurement_ids)
        self.assertIn(procurement2, merged_order.order_line.procurement_ids)

        self.assertEqual(merged_order.incoterm_id, self.incoterm2)
        self.assertEqual(merged_order.payment_term_id, self.payment_term_2)

    def test_20_purchase_merge_order_lines(self):

        """
        Test with two procurements of different quantities
        """

        procurement1 = self.create_procurement_order_3()
        procurement2 = self.create_procurement_order_4()

        self.assertFalse(procurement1.purchase_line_id)
        self.assertFalse(procurement1.purchase_id)
        self.assertFalse(procurement2.purchase_line_id)
        self.assertFalse(procurement2.purchase_id)
        procurement1.run()
        self.assertEqual(procurement1.state, 'buy_to_run')
        procurement2.run()
        self.assertEqual(procurement2.state, 'buy_to_run')

        self.env['procurement.order'].purchase_schedule(compute_all_products=False, compute_product_ids=self.product,
                                                        jobify=False)

        self.assertTrue(procurement1.purchase_id)
        self.assertTrue(procurement1.purchase_line_id)
        order1 = procurement1.purchase_line_id.order_id
        self.assertEqual(order1, procurement1.purchase_id)
        self.assertTrue(procurement2.purchase_line_id)
        order2 = procurement2.purchase_line_id.order_id
        self.assertNotEqual(order1, order2)
        self.assertEqual(len(order1.order_line), 1)
        self.assertEqual(order1.order_line.product_qty, 100)
        self.assertEqual(len(order2.order_line), 1)
        self.assertEqual(order2.order_line.product_qty, 100)
        self.assertEqual(order2, procurement2.purchase_id)

        self.assertEqual(order1.state, 'draft')
        self.assertEqual(order2.state, 'draft')
        order1.write({'incoterm_id': self.incoterm1.id, 'payment_term_id': self.payment_term_1.id})
        order2.write({'incoterm_id': self.incoterm2.id, 'payment_term_id': self.payment_term_2.id})
        self.assertGreater(order1.date_order, order2.date_order)

        result = order1.search([('id', 'in', [order1.id, order2.id])]). \
            with_context(merge_different_dates=True).do_merge()
        list_keys = result.keys()
        self.assertEqual(len(list_keys), 1)
        merged_order_id = list_keys[0]
        lst = result.get(merged_order_id)
        self.assertEqual(len(lst), 2)
        self.assertIn(order1.id, lst)
        self.assertIn(order2.id, lst)
        merged_order = order1.search([('id', '=', merged_order_id)])

        self.assertEqual(len(merged_order), 1)
        self.assertEqual(len(merged_order.order_line), 1)
        self.assertEqual(merged_order.order_line.product_qty, 130)
        self.assertEqual(len(merged_order.order_line.procurement_ids), 2)
        self.assertIn(procurement1, merged_order.order_line.procurement_ids)
        self.assertIn(procurement2, merged_order.order_line.procurement_ids)

        self.assertEqual(merged_order.incoterm_id, self.incoterm2)
        self.assertEqual(merged_order.payment_term_id, self.payment_term_2)

    def test_30_purchase_merge_order_lines(self):

        """
        Test with two procurements of different quantities and no min qty
        """

        self.supplierinfo.min_qty = 0
        self.product.seller_qty = 0

        procurement1 = self.create_procurement_order_3()
        procurement2 = self.create_procurement_order_4()

        self.assertFalse(procurement1.purchase_line_id)
        self.assertFalse(procurement1.purchase_id)
        self.assertFalse(procurement2.purchase_line_id)
        self.assertFalse(procurement2.purchase_id)
        procurement1.run()
        self.assertEqual(procurement1.state, 'buy_to_run')
        procurement2.run()
        self.assertEqual(procurement2.state, 'buy_to_run')

        self.env['procurement.order'].purchase_schedule(compute_all_products=False, compute_product_ids=self.product,
                                                        jobify=False)

        self.assertTrue(procurement1.purchase_id)
        self.assertTrue(procurement1.purchase_line_id)
        order1 = procurement1.purchase_line_id.order_id
        self.assertEqual(order1, procurement1.purchase_id)
        self.assertTrue(procurement2.purchase_line_id)
        order2 = procurement2.purchase_line_id.order_id
        self.assertNotEqual(order1, order2)
        self.assertEqual(len(order1.order_line), 1)
        self.assertEqual(order1.order_line.product_qty, 80)
        self.assertEqual(len(order2.order_line), 1)
        self.assertEqual(order2.order_line.product_qty, 50)
        self.assertEqual(order2, procurement2.purchase_id)

        self.assertEqual(order1.state, 'draft')
        self.assertEqual(order2.state, 'draft')
        order1.write({'incoterm_id': self.incoterm1.id, 'payment_term_id': self.payment_term_1.id})
        order2.write({'incoterm_id': self.incoterm2.id, 'payment_term_id': self.payment_term_2.id})
        self.assertGreater(order1.date_order, order2.date_order)

        result = order1.search([('id', 'in', [order1.id, order2.id])]). \
            with_context(merge_different_dates=True).do_merge()
        list_keys = result.keys()
        self.assertEqual(len(list_keys), 1)
        merged_order_id = list_keys[0]
        lst = result.get(merged_order_id)
        self.assertEqual(len(lst), 2)
        self.assertIn(order1.id, lst)
        self.assertIn(order2.id, lst)
        merged_order = order1.search([('id', '=', merged_order_id)])

        self.assertEqual(len(merged_order), 1)
        self.assertEqual(len(merged_order.order_line), 1)
        self.assertEqual(merged_order.order_line.product_qty, 130)
        self.assertEqual(len(merged_order.order_line.procurement_ids), 2)
        self.assertIn(procurement1, merged_order.order_line.procurement_ids)
        self.assertIn(procurement2, merged_order.order_line.procurement_ids)

        self.assertEqual(merged_order.incoterm_id, self.incoterm2)
        self.assertEqual(merged_order.payment_term_id, self.payment_term_2)
