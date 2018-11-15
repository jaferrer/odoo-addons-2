# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class TestPurchaseInvoicedQuantity(common.TransactionCase):

    def setUp(self):
        super(TestPurchaseInvoicedQuantity, self).setUp()
        self.purchase_order = self.browse_ref('purchase.purchase_order_1')
        self.product1 = self.browse_ref('product.product_product_15')
        self.product2 = self.browse_ref('product.product_product_25')
        self.product3 = self.browse_ref('product.product_product_27')
        self.product_service = self.browse_ref('purchase_invoiced_quantity.product_service')
        self.assertTrue(len(self.purchase_order.order_line), 3)
        self.assertTrue(all([line.product_id.type == 'product' for line in self.purchase_order.order_line]))
        line1, line2, line3 = False, False, False
        for line in self.purchase_order.order_line:
            if line.product_qty == 15 and line.product_id == self.product1 and line.price_unit == 79.80:
                line1 = line
            elif line.product_qty == 5 and line.product_id == self.product2 and line.price_unit == 2868.70:
                line2 = line
            elif line.product_qty == 4 and line.product_id == self.product3 and line.price_unit == 3297.20:
                line3 = line
        self.assertTrue(line1 and line2 and line3)
        self.line1 = line1
        self.line2 = line2
        self.line3 = line3
        self.assertFalse(self.purchase_order.is_service_to_invoice)
        self.assertFalse(self._is_invoice_button_visible())
        self.line4 = self.env['purchase.order.line'].create({
            'order_id': self.purchase_order.id,
            'product_id': self.product_service.id,
            'name': 'line_service',
            'product_qty': 50,
            'price_unit': 500,
            'date_planned': '2018-11-15 12:00:00',
        })
        self.env.invalidate_all()
        self.assertTrue(self.purchase_order.is_service_to_invoice)
        self.line5 = self.env['purchase.order.line'].create({
            'order_id': self.purchase_order.id,
            'product_id': False,
            'name': 'line_no_product',
            'product_qty': 30,
            'price_unit': 800,
            'date_planned': '2018-11-15 12:00:00',
        })
        self.purchase_order.invoice_method = 'picking'
        self.purchase_order.signal_workflow('purchase_confirm')
        self.reception_picking = self.env['stock.picking'].search([('group_id.name', '=', self.purchase_order.name)])
        self.reception_picking.ensure_one()
        self.assertEqual(len(self.reception_picking.move_lines), 3)
        self.assertTrue(self._is_invoice_button_visible())
        self.env.invalidate_all()
        self.assertEqual(self.line1.remaining_invoice_qty, 15)
        self.assertEqual(self.line2.remaining_invoice_qty, 5)
        self.assertEqual(self.line3.remaining_invoice_qty, 4)
        self.assertEqual(self.line4.remaining_invoice_qty, 50)
        self.assertEqual(self.line5.remaining_invoice_qty, 30)

    def _is_invoice_button_visible(self):
        return self.purchase_order.invoice_method == 'picking' and (self.purchase_order.nb_picking_to_invoice != 0 or
                                                                    self.purchase_order.is_service_to_invoice)

    def get_invoice_wizard(self):
        action_invoice_wizard = self.purchase_order.create_invoice()
        context = action_invoice_wizard.get('context')
        self.assertTrue(context)
        # Convert context from string to dict if needed
        if str(context) == context:
            context = eval(context)
        context = dict(context)
        invoice_wizard = self.env['stock.invoice.onshipping'].with_context(context).create({})
        return invoice_wizard

    def test_10_one_reception(self):
        self.reception_picking.action_done()
        self.assertNotEqual(self.reception_picking.invoice_state, 'invoiced')
        self.assertTrue(self._is_invoice_button_visible())
        invoice_wizard = self.get_invoice_wizard()
        self.assertEqual(len(invoice_wizard.service_line_ids), 2)
        for line in invoice_wizard.service_line_ids:
            line.invoice_qty = 0
        invoice_wizard.open_invoice()
        self.env.invalidate_all()
        self.assertEqual(self.reception_picking.invoice_state, 'invoiced')
        self.assertEqual(self.line1.remaining_invoice_qty, 0)
        self.assertEqual(self.line2.remaining_invoice_qty, 0)
        self.assertEqual(self.line3.remaining_invoice_qty, 0)
        self.assertEqual(self.line4.remaining_invoice_qty, 50)
        self.assertEqual(self.line5.remaining_invoice_qty, 30)

    def test_20_two_receptions_and_service(self):
        transfer = self.reception_picking.do_enter_transfer_details()
        transfer_details = self.env['stock.transfer_details'].browse(transfer['res_id'])
        for line in transfer_details.item_ids:
            if line.quantity == 4:
                line.quantity = 2
            elif line.quantity == 5:
                pass
            else:
                line.quantity = 0
        transfer_details.do_detailed_transfer()
        self.assertEqual(self.reception_picking.state, 'done')
        backorder = self.env['stock.picking'].search([('backorder_id', '=', self.reception_picking.id)])
        backorder.ensure_one()
        transfer = backorder.do_enter_transfer_details()
        transfer_details = self.env['stock.transfer_details'].browse(transfer['res_id'])
        for line in transfer_details.item_ids:
            if line.quantity == 2:
                line.quantity = 0
            elif line.quantity == 15:
                line.quantity = 10
        transfer_details.do_detailed_transfer()
        self.assertEqual(backorder.state, 'done')
        self.assertTrue(self._is_invoice_button_visible())
        invoice_wizard = self.get_invoice_wizard()
        self.assertEqual(len(invoice_wizard.service_line_ids), 2)
        for line in invoice_wizard.service_line_ids:
            if line.invoice_qty == 50:
                line.invoice_qty = 15
            elif line.invoice_qty == 30:
                line.invoice_qty = 10
        invoice_wizard.open_invoice()
        self.env.invalidate_all()
        self.assertEqual(self.reception_picking.invoice_state, 'invoiced')
        self.assertEqual(backorder.invoice_state, 'invoiced')
        self.assertEqual(self.line1.remaining_invoice_qty, 5)
        self.assertEqual(self.line2.remaining_invoice_qty, 0)
        self.assertEqual(self.line3.remaining_invoice_qty, 2)
        self.assertEqual(self.line4.remaining_invoice_qty, 35)
        self.assertEqual(self.line5.remaining_invoice_qty, 20)

    def test_30_service_only(self):
        invoice_wizard = self.get_invoice_wizard()
        self.assertEqual(len(invoice_wizard.service_line_ids), 2)
        for line in invoice_wizard.service_line_ids:
            if line.invoice_qty == 50:
                line.invoice_qty = 15
            elif line.invoice_qty == 30:
                line.invoice_qty = 10
        invoice_wizard.open_invoice()
        self.env.invalidate_all()
        self.assertNotEqual(self.reception_picking.invoice_state, 'invoiced')
        self.assertEqual(self.line1.remaining_invoice_qty, 15)
        self.assertEqual(self.line2.remaining_invoice_qty, 5)
        self.assertEqual(self.line3.remaining_invoice_qty, 4)
        self.assertEqual(self.line4.remaining_invoice_qty, 35)
        self.assertEqual(self.line5.remaining_invoice_qty, 20)
