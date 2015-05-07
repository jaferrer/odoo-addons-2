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

class TestOrderQuantities(common.TransactionCase):

    def setUp(self):
        super(TestOrderQuantities, self).setUp()

    def test_10_order_quantity_calculation(self):
        procurement_order_1 = self.browse_ref('purchase_order_quantities_improved.procurement_order_1')
        procurement_order_2 = self.browse_ref('purchase_order_quantities_improved.procurement_order_2')
        procurement_order_3 = self.browse_ref('purchase_order_quantities_improved.procurement_order_3')
        self.assertTrue(procurement_order_1)
        self.assertTrue(procurement_order_2)
        self.assertTrue(procurement_order_3)

        #testing function create under the minimal quantity, then function write under and over the minimal quantity.

        procurement_order_1.run()
        self.assertEqual(procurement_order_1.state, u'running')
        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=', procurement_order_1.product_id.id)])
        self.assertTrue(purchase_order_line)
        # po_qty should be 36
        self.assertEqual(purchase_order_line.product_qty, 36)

        procurement_order_3.run()
        self.assertEqual(procurement_order_3.state, u'running')
        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=', procurement_order_1.product_id.id)])
        self.assertTrue(purchase_order_line)
        # po_qty should be 36
        self.assertEqual(purchase_order_line.product_qty, 36)

        procurement_order_2.run()
        self.assertEqual(procurement_order_2.state, u'running')
        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=', procurement_order_2.product_id.id)])
        self.assertTrue(purchase_order_line)
        # po_qty should be 60
        self.assertEqual(purchase_order_line.product_qty, 60)

    def test_20_order_quantity_calculation(self):

        #testing function create over the maximal quantity

        procurement_order_2 = self.browse_ref('purchase_order_quantities_improved.procurement_order_2')
        procurement_order_2.run()
        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=', procurement_order_2.product_id.id)])
        # po_qty should be 48
        self.assertEqual(purchase_order_line.product_qty, 48)

    def test_30_order_quantity_calculation(self):

        #testing how different uom are working together

        procurement_order_4 = self.browse_ref('purchase_order_quantities_improved.procurement_order_4')
        procurement_order_4.run()
        self.assertEqual(procurement_order_4.state, u'running')
        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=', procurement_order_4.product_id.id)])
        self.assertTrue(purchase_order_line)
        # po_qty should be 4
        self.assertEqual(purchase_order_line.product_qty, 4)

    def test_40_order_quantity_calculation(self):

        #testing modified functions create and write: when the po is created by the operator, those two functions should not overwrite it
        #when creation a procurement order line, product_qty can not be under the product_min_qty: useless to test this situation

        supplier1 = self.browse_ref('purchase_order_quantities_improved.supplier1')
        self.assertTrue(supplier1)
        location1 = self.browse_ref('stock.stock_location_stock')
        self.assertTrue(location1)
        pricelist1 = self.browse_ref('purchase.list0')
        self.assertTrue(pricelist1)
        product1 = self.browse_ref('purchase_order_quantities_improved.product1')
        self.assertTrue(product1)

        purchase_order_1 = self.env['purchase.order'].create({
            "name": 'Purchase order 1',
            "partner_id": supplier1.id,
            "date_order": '2015-05-04 15:00:00',
            "location_id": location1.id,
            "pricelist_id": pricelist1.id,
        })

        purchase_order_line_1 = self.env['purchase.order.line'].create({
            "name": "Purchase order line 1",
            "product_id": product1.id,
            "price_unit": 10.0,
            "order_id": purchase_order_1.id,
            "product_qty": 3.5,
            "date_planned": '2015-05-04 15:00:00',
        })

        # po_qty should be still 3.5 (testing function create which should not be modified at that time
        self.assertEqual(purchase_order_line_1.product_qty, 3.5)

        purchase_order_line_1.product_qty = 5.5

        # po_qty should be still 5.5 (testing function write, which should not be modified at that time
        self.assertEqual(purchase_order_line_1.product_qty, 5.5)