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


class TestSupplierPriceValidity(common.TransactionCase):

    def setUp(self):
        super(TestSupplierPriceValidity, self).setUp()


    def test_10_price_validity(self):

        """Test of price calculation by function onchange_product_id from purchase_order_line model"""

        self.browse_ref('purchase.ver0').items_id[0].base = -2
        product1 = self.browse_ref('product_supplier_price_validity.product1')
        self.assertTrue(product1)
        product1.route_ids = [(4, self.ref("purchase.route_warehouse0_buy"))]
        supplier1 = self.browse_ref('product_supplier_price_validity.supplier1')
        self.assertTrue(supplier1)
        location1 = self.browse_ref('stock.stock_location_stock')
        self.assertTrue(location1)
        pricelist = self.browse_ref('purchase.list0')
        self.assertTrue(pricelist)

        # order year 2015

        purchase_order_1 = self.env['purchase.order'].create({
            "name": 'Purchase order 1',
            "partner_id": supplier1.id,
            "date_order": '2015-05-04 15:00:00',
            "location_id": location1.id,
            "pricelist_id": pricelist.id,
        })

        purchase_order_line = self.env['purchase.order.line'].create({
            "name": "Purchase order line 1",
            "product_id": product1.id,
            "price_unit": 1.0,
            "order_id": purchase_order_1.id,
            "product_qty": 1.0,
            "date_planned": '2015-05-04 15:00:00',
        })

        def unit_price(line):
            results = line.onchange_product_id(line.order_id.pricelist_id.id,
                                                              line.product_id.id,
                                                              line.product_qty,
                                                              line.product_uom.id,
                                                              line.order_id.partner_id.id,
                                                              line.order_id.date_order)
            return (results['value'])['price_unit']

        self.assertEquals(unit_price(purchase_order_line), 14)

        purchase_order_line.product_qty = 11.0
        self.assertEquals(unit_price(purchase_order_line), 12)
        purchase_order_line.product_qty = 101.0
        self.assertEquals(unit_price(purchase_order_line), 10)
        purchase_order_line.product_qty = 1001.0
        self.assertEquals(unit_price(purchase_order_line), 8)
        purchase_order_line.product_qty = 10001.0
        self.assertEquals(unit_price(purchase_order_line), 5)

        # order year 2017

        purchase_order_2 = self.env['purchase.order'].create({
            "name": 'Purchase order 2',
            "partner_id": supplier1.id,
            "date_order": '2017-05-04 15:00:00',
            "location_id": location1.id,
            "pricelist_id": pricelist.id,
        })

        purchase_order_line2 = self.env['purchase.order.line'].create({
            "name": "Purchase order line 2",
            "product_id": product1.id,
            "price_unit": 1.0,
            "order_id": purchase_order_2.id,
            "product_qty": 1.0,
            "date_planned": '2017-05-04 15:00:00',
        })

        self.assertEquals(unit_price(purchase_order_line2), 13)
        purchase_order_line2.product_qty = 11.0
        self.assertEquals(unit_price(purchase_order_line2), 11)
        purchase_order_line2.product_qty = 101.0
        self.assertEquals(unit_price(purchase_order_line2), 9)
        purchase_order_line2.product_qty = 1001.0
        self.assertEquals(unit_price(purchase_order_line2), 8)
        purchase_order_line2.product_qty = 10001.0
        self.assertEquals(unit_price(purchase_order_line2), 5)

    def test_20_price_validity(self):

        """Test of price calculation by creation of procurement orders"""

        self.browse_ref('purchase.ver0').items_id[0].base = -2

        supplier1 = self.browse_ref('product_supplier_price_validity.supplier1')
        self.assertTrue(supplier1)
        product1 = self.browse_ref('product_supplier_price_validity.product1')
        self.assertTrue(product1)
        product1.route_ids = [(4, self.ref("purchase.route_warehouse0_buy"))]
        location1 = self.browse_ref('stock.stock_location_stock')
        self.assertTrue(location1)
        pricelist = self.browse_ref('purchase.list0')
        self.assertTrue(pricelist)
        warehouse = self.browse_ref('stock.warehouse0')
        self.assertTrue(warehouse)
        uom = self.browse_ref('product.product_uom_unit')
        self.assertTrue(uom)

        # demo procurement order

        procurement_order_1 = self.env['procurement.order'].create({
            "name": 'Procurement order 1',
            "product_id": product1.id,
            "product_qty": 1.0,
            "warehouse_id": warehouse.id,
            "location_id": location1.id,
            "date_planned": '2015-05-04 15:00:00',
            "product_uom": uom.id,
            })

        def test(qty, result):
            procurement_order_1.product_qty = qty
            procurement_order_1.run()
            self.assertEqual(procurement_order_1.state, u'running')
            purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=', procurement_order_1.product_id.id)])
            self.assertTrue(purchase_order_line)
            # po price_unit should be equal to result:
            self.assertEqual(purchase_order_line.price_unit, result)
            purchase_order_line.order_id.unlink()

        test(1.0, 14)
        test(9.0, 14)
        test(10.0, 12)
        test(11.0, 12)
        test(99.0, 12)
        test(100.0, 10)
        test(101.0, 10)
        test(999.0, 10)
        test(1000.0, 8)
        test(1001.0, 8)
        test(9999.0, 8)
        test(10000.0, 5)
        test(10001.0, 5)

        procurement_order_1.date_planned = "2017-05-04 15:00:00"

        test(1.0, 13)
        test(9.0, 13)
        test(10.0, 11)
        test(11.0, 11)
        test(99.0, 11)
        test(100.0, 9)
        test(101.0, 9)
        test(999.0, 9)
        test(1000.0, 8)
        test(1001.0, 8)
        test(9999.0, 8)
        test(10000.0, 5)
        test(10001.0, 5)