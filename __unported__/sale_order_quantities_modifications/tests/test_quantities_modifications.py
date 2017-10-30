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

from dateutil.relativedelta import relativedelta

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

from openerp import fields

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

    def test_10_quantities_modifications(self):

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
                self.assertIn(t, [[p.product_id, p.product_qty] for p in procurements])

        lines = [self.sale_order_line1.id, self.sale_order_line2.id, self.sale_order_line3.id]

        self.sale_order.signal_workflow('order_confirm')
        self.assertEqual(self.sale_order.state, 'manual')
        self.assertEqual(self.sale_order_line1.state, 'confirmed')
        self.assertEqual(self.sale_order_line2.state, 'confirmed')
        self.assertEqual(self.sale_order_line3.state, 'confirmed')
        self.assertTrue(self.sale_order_line1.procurement_ids)
        self.assertTrue(self.sale_order_line2.procurement_ids)
        self.assertTrue(self.sale_order_line3.procurement_ids)
        check_procurements(lines, [[self.product1, 4], [self.product2, 5], [self.product3, 6]])

        # Two quantities increased, one decreased, and modification of price_unit:
        move = self.env['stock.move'].search([('product_id', '=', self.product3.id),
                                               ('procurement_id', 'in', self.sale_order_line3.procurement_ids.ids),
                                               ('state', 'not in', ['draft', 'cancel', 'done'])])
        self.assertEqual(len(move), 1)
        self.sale_order.write({'order_line': [[1, self.sale_order_line1.id, {'product_uom_qty': 5}],
                                              [1, self.sale_order_line2.id, {'product_uom_qty': 4}],
                                              [1,self.sale_order_line3.id, {'product_uom_qty': 7, 'price_unit': 1.5}]]})
        check_procurements(lines, [[self.product1, 4], [self.product1, 1], [self.product2, 4],
                                   [self.product3, 6], [self.product3, 1]])
        self.assertEqual(move.price_unit, 1.5)

         # Two quantities decreased, one increased:
        self.sale_order.write({'order_line': [[1, self.sale_order_line1.id, {'product_uom_qty': 4}],
                                              [1, self.sale_order_line2.id, {'product_uom_qty': 3}],
                                              [1,self.sale_order_line3.id, {'product_uom_qty': 8}]]})
        check_procurements(lines, [[self.product1, 4], [self.product2, 3],
                                   [self.product3, 6], [self.product3, 1], [self.product3, 1]])

        #Two quantities increased, one decreased, one line added
        self.sale_order.write({'order_line': [[1, self.sale_order_line1.id, {'product_uom_qty': 5}],
                                              [1, self.sale_order_line2.id, {'product_uom_qty': 4}],
                                              [1,self.sale_order_line3.id, {'product_uom_qty': 7}]]})
        line4 = self.env['sale.order.line'].create({
            'name': "Sale Order Line 4 (Quantities Mofifications)",
            'order_id': self.sale_order.id,
            'product_id': self.product1.id,
            'product_uom_qty': 10.0,
            'price_unit': 4.0,
        })
        lines += [line4.id]
        check_procurements(lines, [[self.product1, 1], [self.product1, 4], [self.product2, 3], [self.product2, 1],
                                   [self.product3, 7], [self.product1, 10]])

         # One quantity decreased, one increased, and two lines deleted
        self.sale_order.write({'order_line': [[1, self.sale_order_line1.id, {'product_uom_qty': 2}],
                                              [1, self.sale_order_line3.id, {'product_uom_qty': 15}]]})
        self.sale_order_line2.unlink()
        line4.unlink()
        lines = [self.sale_order_line1.id, self.sale_order_line3.id]
        check_procurements(lines, [[self.product1, 2], [self.product3, 7], [self.product3, 8]])
