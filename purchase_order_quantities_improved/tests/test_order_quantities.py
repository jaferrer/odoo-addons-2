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
        self.supplier1 = self.browse_ref('purchase_order_quantities_improved.supplier1')
        self.location1 = self.browse_ref('stock.stock_location_stock')
        self.picking_type_internal = self.browse_ref('stock.picking_type_internal')
        self.pricelist1 = self.browse_ref('product.list0')
        self.product1 = self.browse_ref('purchase_order_quantities_improved.product1')
        self.supplierinfo1 = self.browse_ref('purchase_order_quantities_improved.supplierinfo1')
        self.supplierinfo2 = self.browse_ref('purchase_order_quantities_improved.supplierinfo2')

    def test_10_order_quantity_calculation(self):
        """
        Testing function create under the minimal quantity, then function write under and over the minimal quantity.
        """
        procurement_order_1 = self.env['procurement.order'].create({
            'name': "Procurement Order 1",
            'product_id': self.ref('purchase_order_quantities_improved.product1'),
            'product_qty': 7,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock.stock_location_stock'),
            'date_planned': "2015-05-04 15:00:00",
            'product_uom': self.ref('product.product_uom_unit')
        })
        procurement_order_1.run()
        self.assertEqual(procurement_order_1.state, u'running')
        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=',
                                                                       procurement_order_1.product_id.id)])
        self.assertTrue(purchase_order_line)
        self.assertEqual(len(purchase_order_line), 1)
        # po_qty should be 36
        self.assertEqual(purchase_order_line.product_qty, 36)

        procurement_order_3 = self.env['procurement.order'].create({
            'name': "Procurement Order 3",
            'product_id': self.ref('purchase_order_quantities_improved.product1'),
            'product_qty': 7,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock.stock_location_stock'),
            'date_planned': "2015-05-04 15:00:00",
            'product_uom': self.ref('product.product_uom_unit')
        })
        procurement_order_3.run()
        self.assertEqual(procurement_order_3.state, u'running')
        purchase_order_line = self.env['purchase.order.line']. \
            search([('product_id', '=', procurement_order_1.product_id.id)])
        self.assertTrue(purchase_order_line)
        # po_qty should be 36
        self.assertEqual(purchase_order_line.product_qty, 36)

        procurement_order_2 = self.env['procurement.order'].create({
            'name': "Procurement Order 2",
            'product_id': self.ref('purchase_order_quantities_improved.product1'),
            'product_qty': 40,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock.stock_location_stock'),
            'date_planned': "2015-05-04 15:00:00",
            'product_uom': self.ref('product.product_uom_unit')
        })
        procurement_order_2.run()
        self.assertEqual(procurement_order_2.state, u'running')
        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=',
                                                                       procurement_order_2.product_id.id)])
        self.assertTrue(purchase_order_line)
        # po_qty should be 60
        self.assertEqual(purchase_order_line.product_qty, 60)

    def test_20_order_quantity_calculation(self):
        """
        Testing function create over the maximal quantity.
        """
        procurement_order_2 = self.env['procurement.order'].create({
            'name': "Procurement Order 2",
            'product_id': self.ref('purchase_order_quantities_improved.product1'),
            'product_qty': 40,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock.stock_location_stock'),
            'date_planned': "2015-05-04 15:00:00",
            'product_uom': self.ref('product.product_uom_unit')
        })
        procurement_order_2.run()
        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=',
                                                                       procurement_order_2.product_id.id)])
        # po_qty should be 48
        self.assertEqual(purchase_order_line.product_qty, 48)

    def test_30_order_quantity_calculation(self):
        """
        Testing how different uom are working together
        """
        procurement_order_4 = self.env['procurement.order'].create({
            'name': "Procurement Order 4",
            'product_id': self.ref('purchase_order_quantities_improved.product2'),
            'product_qty': 3,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock.stock_location_stock'),
            'date_planned': "2015-05-04 15:00:00",
            'product_uom': self.ref('product.product_uom_unit')
        })
        procurement_order_4.run()
        self.assertEqual(procurement_order_4.state, u'running')
        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=',
                                                                       procurement_order_4.product_id.id)])
        self.assertTrue(purchase_order_line)
        # po_qty should be 4
        self.assertEqual(purchase_order_line.product_qty, 4)

    def test_40_order_quantity_calculation(self):
        """
        Testing modified functions create and write.
        When the po is created by the operator, those two functions should not overwrite it when creation a
        procurement order line, product_qty can not be under the product_min_qty: useless to test this situation
        """

        purchase_order_1 = self.env['purchase.order'].create({
            "name": 'Purchase order 1',
            "partner_id": self.supplier1.id,
            "date_order": '2015-05-04 15:00:00',
            "picking_type_id": self.picking_type_internal.id,
        })

        purchase_order_line_1 = self.env['purchase.order.line'].create({
            "name": "Purchase order line 1",
            "product_id": self.product1.id,
            "product_uom": self.product1.uom_po_id.id,
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

    def test_50_order_quantity_calculation(self):
        """
        Testing calculation without supplierinfo
        """

        procurement_order_1 = self.env['procurement.order'].create({
            'name': "Procurement Order 1",
            'product_id': self.ref('purchase_order_quantities_improved.product1'),
            'product_qty': 7,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock.stock_location_stock'),
            'date_planned': "2015-05-04 15:00:00",
            'product_uom': self.ref('product.product_uom_unit')
        })
        procurement_order_1.run()
        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=',
                                                                       procurement_order_1.product_id.id)])
        self.assertTrue(purchase_order_line)
        # po_qty should be 36
        self.assertEqual(purchase_order_line.product_qty, 36)

        procurement_order_3 = self.env['procurement.order'].create({
            'name': "Procurement Order 3",
            'product_id': self.ref('purchase_order_quantities_improved.product1'),
            'product_qty': 7,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock.stock_location_stock'),
            'date_planned': "2015-05-04 15:00:00",
            'product_uom': self.ref('product.product_uom_unit')
        })
        procurement_order_3.run()
        self.assertEqual(procurement_order_3.state, u'running')
        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=',
                                                                       procurement_order_1.product_id.id)])
        self.assertTrue(purchase_order_line)
        # po_qty should be 36
        self.assertEqual(purchase_order_line.product_qty, 36)

        self.supplierinfo1.unlink()
        self.supplierinfo2.unlink()
        procurement_order_3.cancel()

        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=',
                                                                       procurement_order_1.product_id.id)])
        self.assertTrue(purchase_order_line)
        # po_qty should be 7
        self.assertEqual(purchase_order_line.product_qty, 7)
