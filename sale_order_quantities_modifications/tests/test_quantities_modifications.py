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

from openerp import exceptions
from openerp.tests import common


class TestQuantitiesModifications(common.TransactionCase):

    def setUp(self):
        super(TestQuantitiesModifications, self).setUp()
        self.product1 = self.browse_ref('sale_order_quantities_modifications.product1')
        self.product2 = self.browse_ref('sale_order_quantities_modifications.product2')
        self.product3 = self.browse_ref('sale_order_quantities_modifications.product3')
        self.sale_order = self.browse_ref('sale_order_quantities_modifications.sale_order')
        self.sale_order_line1 = self.browse_ref('sale_order_quantities_modifications.sale_order_line1')
        self.sale_order_line2 = self.browse_ref('sale_order_quantities_modifications.sale_order_line2')
        self.sale_order_line3 = self.browse_ref('sale_order_quantities_modifications.sale_order_line3')
        self.unit = self.browse_ref('product.product_uom_unit')
        self.dozen = self.browse_ref('product.product_uom_dozen')

    def test_10_quantities_modifications(self):
        """
        Test simple case
        """

        # First, testing that the 'write' function does not create procurements at draft state
        self.assertEqual(self.sale_order.state, 'draft')
        self.sale_order_line1.product_uom_qty = 4
        self.assertEqual(len(self.sale_order.order_line), 3)
        for l in self.sale_order.order_line:
            self.assertFalse(l.procurement_ids)

        def check_procurements(lines, list_procurements):
            procurements = self.env['procurement.order'].search([('sale_line_id', 'in', lines)])
            self.assertEqual(len(list_procurements), len(procurements))
            for t in list_procurements:
                self.assertIn(t, [(p.product_id, p.product_qty, p.product_uos_qty) for p in procurements])

        lines = [self.sale_order_line1.id, self.sale_order_line2.id, self.sale_order_line3.id]

        self.sale_order.signal_workflow('order_confirm')
        self.assertEqual(self.sale_order.state, 'manual')
        self.assertEqual(self.sale_order_line1.state, 'confirmed')
        self.assertEqual(self.sale_order_line2.state, 'confirmed')
        self.assertEqual(self.sale_order_line3.state, 'confirmed')
        self.assertTrue(self.sale_order_line1.procurement_ids)
        self.assertTrue(self.sale_order_line2.procurement_ids)
        self.assertTrue(self.sale_order_line3.procurement_ids)
        check_procurements(lines, [(self.product1, 4, 4), (self.product2, 5, 5), (self.product3, 6, 6)])

        # Two quantities increased, one decreased, and modification of price_unit:
        move = self.env['stock.move'].search([('product_id', '=', self.product3.id),
                                              ('procurement_id', 'in', self.sale_order_line3.procurement_ids.ids),
                                              ('state', 'not in', ['draft', 'cancel', 'done'])])
        self.assertEqual(len(move), 1)
        self.sale_order_line1.product_uom_qty = 5
        self.sale_order_line2.product_uom_qty = 4
        self.sale_order_line3.write({'product_uom_qty': 7, 'price_unit': 1.5})
        check_procurements(lines, [(self.product1, 4, 4), (self.product1, 1, 1), (self.product2, 4, 4),
                                   (self.product3, 6, 6), (self.product3, 1, 1)])
        self.assertEqual(move.price_unit, 1.5)

        # Two quantities decreased, one increased:
        self.sale_order_line1.product_uom_qty = 4
        self.sale_order_line2.product_uom_qty = 3
        self.sale_order_line3.product_uom_qty = 8
        check_procurements(lines, [(self.product1, 4, 4), (self.product2, 3, 3),
                                   (self.product3, 6, 6), (self.product3, 1, 1), (self.product3, 1, 1)])

        # Two quantities increased, one decreased, one line added
        self.sale_order_line1.product_uom_qty = 5
        self.sale_order_line2.product_uom_qty = 4
        self.sale_order_line3.product_uom_qty = 7

        line4 = self.env['sale.order.line'].create({
            'name': "Sale Order Line 4 (Quantities Mofifications)",
            'order_id': self.sale_order.id,
            'product_id': self.product1.id,
            'product_uom_qty': 10.0,
            'price_unit': 4.0,
        })
        lines += [line4.id]
        check_procurements(lines, [(self.product1, 1, 1), (self.product1, 4, 4), (self.product2, 3, 3),
                                   (self.product2, 1, 1), (self.product3, 7, 7), (self.product1, 10, 10)])

        # One quantity decreased, one increased, and two lines deleted
        self.sale_order_line1.product_uom_qty = 2
        self.sale_order_line3.product_uom_qty = 15
        self.sale_order_line2.unlink()
        line4.unlink()
        lines = [self.sale_order_line1.id, self.sale_order_line3.id]
        check_procurements(lines, [(self.product1, 2, 2), (self.product3, 7, 7), (self.product3, 8,8)])

    def test_20_quantities_modifications(self):
        """
        Test with several procurements on a sale order line (and different states on procurements).
        """

        self.sale_order.signal_workflow('order_confirm')
        old_procurement = self.sale_order_line1.procurement_ids
        self.assertEqual(len(old_procurement), 1)
        self.assertEqual(old_procurement.product_qty, 8)
        self.sale_order_line1.product_uom_qty = 14
        new_procurement = self.sale_order_line1.procurement_ids.filtered(lambda proc: proc != old_procurement)
        self.assertEqual(len(new_procurement), 1)
        self.assertEqual(new_procurement.product_qty, 6)

        # Let's set old procurement to state done.
        picking = self.sale_order.picking_ids
        self.assertEqual(len(picking), 1)
        self.assertEqual(len(picking.move_lines), 4)
        move1 = picking.move_lines.filtered(lambda move: move.product_id == self.product1 and move.product_uom_qty == 8)
        move2 = picking.move_lines.filtered(lambda move: move.product_id == self.product1 and move.product_uom_qty == 6)
        self.assertTrue(move1 and move2)
        self.assertEqual(move1.product_uom, self.unit)
        self.assertEqual(move2.product_uom, self.unit)
        self.assertEqual(move1.product_uos_qty, 8)
        self.assertEqual(move2.product_uos_qty, 6)
        move1.action_done()
        self.assertEqual(old_procurement.state, 'done')

        # Let's increase line quantity
        self.sale_order_line1.product_uom_qty = 18
        self.assertEqual(len(self.sale_order_line1.procurement_ids), 3)
        self.assertIn(old_procurement, self.sale_order_line1.procurement_ids)
        self.assertIn(new_procurement, self.sale_order_line1.procurement_ids)
        new_procurement2 = self.sale_order_line1.procurement_ids. \
            filtered(lambda proc: proc not in [old_procurement, new_procurement])
        self.assertEqual(new_procurement2.product_qty, 4)

        # Let's try to set line quantity to zero : it should not be possible.
        with self.assertRaises(exceptions.except_orm):
            self.sale_order_line1.product_uom_qty = 0

        # Let's decrease strongly line quantity : it should not be possible to cancel a done procurement
        with self.assertRaises(exceptions.except_orm):
            self.sale_order_line1.product_uom_qty = 7

        # Let's decrease slightly line quantity : it should not unlink old_procurement
        unlink_ids = [new_procurement.id, new_procurement2.id]
        self.sale_order_line1.product_uom_qty = 10
        # New procurements should have been deleted
        self.assertFalse(self.env['procurement.order'].search([('id', 'in', unlink_ids)]))
        # Old procurement should not have been deleted
        self.assertIn(old_procurement, self.sale_order_line1.procurement_ids)
        self.assertEqual(len(self.sale_order_line1.procurement_ids), 2)
        new_procurement = self.sale_order_line1.procurement_ids.filtered(lambda proc: proc != old_procurement)
        self.assertTrue(new_procurement)
        self.assertEqual(new_procurement.product_qty, 2)

    def test_30_quantities_modifications(self):
        """
        Test with different UOM between procurements and lines.
        """

        self.sale_order.signal_workflow('order_confirm')
        old_procurement = self.sale_order_line1.procurement_ids
        self.assertEqual(len(old_procurement), 1)
        self.assertEqual(old_procurement.product_qty, 8)
        self.sale_order_line1.product_uom_qty = 12
        new_procurement = self.sale_order_line1.procurement_ids.filtered(lambda proc: proc != old_procurement)
        self.assertEqual(len(new_procurement), 1)
        self.assertEqual(new_procurement.product_qty, 4)

        # Let's set old procurement to state done.
        picking = self.sale_order.picking_ids
        self.assertEqual(len(picking), 1)
        self.assertEqual(len(picking.move_lines), 4)
        move1 = picking.move_lines.filtered(lambda move: move.product_id == self.product1 and move.product_uom_qty == 8)
        move2 = picking.move_lines.filtered(lambda move: move.product_id == self.product1 and move.product_uom_qty == 4)
        self.assertTrue(move1 and move2)
        self.assertEqual(move1.product_uom, self.unit)
        self.assertEqual(move2.product_uom, self.unit)
        self.assertEqual(move1.product_uos_qty, 8)
        self.assertEqual(move2.product_uos_qty, 4)
        move1.action_done()
        self.assertEqual(old_procurement.state, 'done')

        # Let's increase line quantity
        self.sale_order_line1.write({'product_uom_qty': 2, 'product_uom': self.dozen.id})
        self.assertEqual(len(self.sale_order_line1.procurement_ids), 3)
        self.assertIn(old_procurement, self.sale_order_line1.procurement_ids)
        self.assertIn(new_procurement, self.sale_order_line1.procurement_ids)
        new_procurement2 = self.sale_order_line1.procurement_ids. \
            filtered(lambda proc: proc not in [old_procurement, new_procurement])
        self.assertEqual(new_procurement2.product_qty, 1)
        self.assertEqual(new_procurement2.product_uom, self.dozen)

        # Let's try to set line quantity to zero : it should not be possible.
        with self.assertRaises(exceptions.except_orm):
            self.sale_order_line1.product_uom_qty = 0

        # Let's decrease strongly line quantity : it should not be possible to cancel a done procurement
        with self.assertRaises(exceptions.except_orm):
            self.sale_order_line1.product_uom_qty = 0.1

        # Let's decrease slightly line quantity : it should not unlink old_procurement
        unlink_ids = [new_procurement.id, new_procurement2.id]
        self.sale_order_line1.product_uom_qty = 1
        # New procurements should have been deleted
        self.assertFalse(self.env['procurement.order'].search([('id', 'in', unlink_ids)]))
        # Old procurement should not have been deleted
        self.assertIn(old_procurement, self.sale_order_line1.procurement_ids)
        self.assertEqual(len(self.sale_order_line1.procurement_ids), 2)
        new_procurement = self.sale_order_line1.procurement_ids.filtered(lambda proc: proc != old_procurement)
        self.assertTrue(new_procurement)
        self.assertEqual(new_procurement.product_qty, 0.33)
        self.assertEqual(new_procurement.product_uom, self.dozen)
