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
        self.procurement1 = self.browse_ref('purchase_merge_order_lines.procurement1')
        self.procurement2 = self.browse_ref('purchase_merge_order_lines.procurement2')
        self.incoterm1 = self.browse_ref('stock.incoterm_EXW')
        self.incoterm2 = self.browse_ref('stock.incoterm_FCA')
        self.payment_term_1 = self.browse_ref('account.account_payment_term_15days')
        self.payment_term_2 = self.browse_ref('account.account_payment_term')

    def test_10_purchase_merge_order_lines(self):

        self.assertEqual(self.procurement1.state, 'confirmed')
        self.assertEqual(self.procurement2.state, 'confirmed')
        self.assertFalse(self.procurement1.purchase_line_id)
        self.assertFalse(self.procurement1.purchase_id)
        self.assertFalse(self.procurement2.purchase_line_id)
        self.assertFalse(self.procurement2.purchase_id)
        self.procurement1.run()
        self.assertTrue(self.procurement1.purchase_id)
        self.assertTrue(self.procurement1.purchase_line_id)
        order1 = self.procurement1.purchase_line_id.order_id
        self.assertEqual(order1, self.procurement1.purchase_id)
        # order1.action_cancel()

        self.procurement2.run()
        self.assertTrue(self.procurement2.purchase_line_id)
        order2 = self.procurement2.purchase_line_id.order_id
        self.assertNotEqual(order1, order2)
        self.assertEqual(len(order1.order_line), 1)
        self.assertEqual(order1.order_line.product_qty, 100)
        self.assertEqual(len(order2.order_line), 1)
        self.assertEqual(order2.order_line.product_qty, 100)
        self.assertEqual(order2, self.procurement2.purchase_id)
        # order1.action_cancel_draft()

        self.assertEqual(order1.state, 'draft')
        self.assertEqual(order2.state, 'draft')
        order1.write({'incoterm_id': self.incoterm1.id, 'payment_term_id': self.payment_term_1.id})
        order2.write({'incoterm_id': self.incoterm2.id, 'payment_term_id': self.payment_term_2.id})
        self.assertGreater(order1.date_order, order2.date_order)

        result = order1.search([('id', 'in', [order1.id, order2.id])]). \
            with_context(merge_different_dates=True).do_merge()
        lst = result.get(order2.id + 1)
        self.assertEqual(len(lst), 2)
        self.assertIn(order1.id, lst)
        self.assertIn(order2.id, lst)
        merged_order = order1.search([('id', '=', order2.id + 1)])

        self.assertEqual(len(merged_order), 1)
        self.assertEqual(len(merged_order.order_line), 1)
        self.assertEqual(merged_order.order_line.product_qty, 160)
        self.assertEqual(len(merged_order.order_line.procurement_ids), 2)
        self.assertIn(self.procurement1, merged_order.order_line.procurement_ids)
        self.assertIn(self.procurement2, merged_order.order_line.procurement_ids)

        self.assertEqual(merged_order.incoterm_id, self.incoterm2)
        self.assertEqual(merged_order.payment_term_id, self.payment_term_2)
