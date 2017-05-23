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

from openerp import fields
from openerp.tests import common


class TestStockProcurementSplit(common.TransactionCase):

    def setUp(self):
        super(TestStockProcurementSplit, self).setUp()
        self.location_a = self.browse_ref('stock_procurement_split.stock_location_a')
        self.location_b = self.browse_ref('stock_procurement_split.stock_location_b')
        self.location_c = self.browse_ref('stock_procurement_split.stock_location_c')
        self.product = self.browse_ref('stock_procurement_split.product_test_product')
        self.product_uom_unit_id = self.ref('product.product_uom_unit')

    def test_10_split_and_cancel(self):
        """Test that a split correctly splits the procs and then check chain cancellation"""
        proc_c = self.env['procurement.order'].create({
            'name': "Procurement in C",
            'date_planned': '2015-03-19 18:00:00',
            'product_id': self.product.id,
            'product_qty': 5,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_c.id
        })
        proc_c.run()
        self.assertEqual(proc_c.state, 'running')
        self.assertEqual(len(proc_c.move_ids), 1)
        move_b_c = proc_c.move_ids[0]
        self.assertEqual(move_b_c.state, 'waiting')
        self.assertEqual(move_b_c.product_qty, 5)
        self.assertEqual(move_b_c.location_id, self.location_b)

        proc_b = self.env['procurement.order'].search([('move_dest_id', '=', move_b_c.id)])
        self.assertEqual(len(proc_b), 1)
        proc_b.run()
        self.assertEqual(proc_b.state, 'running')
        self.assertEqual(len(proc_b.move_ids), 1)
        move_a_b = proc_b.move_ids[0]
        self.assertEqual(move_a_b.state, 'confirmed')
        self.assertEqual(move_a_b.product_qty, 5)
        self.assertEqual(move_a_b.location_id, self.location_a)

        split_move_id = self.env['stock.move'].split(move_a_b, 2)
        self.assertEqual(proc_b.product_qty, 3)
        self.assertEqual(proc_c.product_qty, 3)
        self.assertEqual(move_a_b.product_qty, 3)
        self.assertEqual(move_b_c.product_qty, 3)

        split_move = self.env['stock.move'].browse(split_move_id)
        self.assertEqual(split_move.product_qty, 2)
        split_proc_b = split_move.procurement_id
        self.assertTrue(split_proc_b)
        self.assertEqual(split_proc_b.product_qty, 2)
        split_move_b_to_c = split_move.move_dest_id
        self.assertTrue(split_move_b_to_c)
        self.assertEqual(split_proc_b.move_dest_id, split_move_b_to_c)
        self.assertEqual(split_move_b_to_c.product_qty, 2)
        self.assertTrue(split_move_b_to_c.procurement_id)
        split_proc_c = split_move_b_to_c.procurement_id
        self.assertEqual(split_proc_c.product_qty, 2)

        split_proc_c.cancel()
        self.assertEqual(split_proc_c.state, 'cancel')
        self.assertEqual(split_move_b_to_c.state, 'cancel')
        self.assertEqual(split_proc_b.state, 'cancel')
        self.assertEqual(split_move.state, 'cancel')

        self.assertEqual(proc_c.state, 'running')
        self.assertEqual(move_b_c.state, 'waiting')
        self.assertEqual(proc_b.state, 'running')
        self.assertEqual(move_a_b.state, 'confirmed')

        proc_c.cancel()
        self.assertEqual(proc_c.state, 'cancel')
        self.assertEqual(move_b_c.state, 'cancel')
        self.assertEqual(proc_b.state, 'cancel')
        self.assertEqual(move_a_b.state, 'cancel')
