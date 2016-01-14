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


class TestStockSplitPicking(common.TransactionCase):

    def setUp(self):
        super(TestStockSplitPicking, self).setUp()
        self.product = self.browse_ref('stock_split_picking.product_test_stock_split_picking')
        self.picking = self.browse_ref('stock_split_picking.test_picking')
        self.move = self.browse_ref('stock_split_picking.test_stock_move')

    def test_10_stock_split_picking(self):

        ##############################################
        # First, without saving packops
        ##############################################

        self.env['stock.quant'].search([('product_id', '=', self.product.id)]).unlink()

        self.assertTrue(self.product and self.picking and self.move)
        self.picking.action_confirm()
        self.picking.force_assign()
        self.assertEqual(self.picking.move_lines, self.move)
        self.assertEqual(self.picking.state, 'assigned')
        self.assertFalse(self.picking.packing_details_saved)

        self.picking.rereserve_pick()
        self.assertFalse(self.picking.pack_operation_ids)

        # Preparing packops without saving it
        popup = self.env['stock.transfer_details'].\
            with_context(self.picking.do_enter_transfer_details().get('context')).\
            create({'picking_id': self.picking.id})
        self.assertEqual(len(popup.item_ids), 1)
        self.assertEqual(len(self.picking.pack_operation_ids), 1)
        self.assertEqual(self.picking.pack_operation_ids.product_qty, 30)

        # Decreasing qty and then rereserve_pick
        self.picking.pack_operation_ids.product_qty = 20
        self.assertFalse(self.picking.packing_details_saved)
        self.picking.rereserve_pick()
        self.assertEqual(len(self.picking.pack_operation_ids), 1)
        self.assertEqual(self.picking.pack_operation_ids.product_qty, 30)

        # Rereserve pick again and check that nothing has changed
        self.picking.rereserve_pick()
        self.assertEqual(len(self.picking.pack_operation_ids), 1)
        self.assertEqual(self.picking.pack_operation_ids.product_qty, 30)

        # Increasing qty and then rereserve_pick
        self.picking.pack_operation_ids.product_qty = 40
        self.assertFalse(self.picking.packing_details_saved)
        self.picking.rereserve_pick()
        self.assertEqual(len(self.picking.pack_operation_ids), 1)
        self.assertEqual(self.picking.pack_operation_ids.product_qty, 30)

        ##############################################
        # Now, let's save packops
        ##############################################

        # Preparing packops and saving it
        popup = self.env['stock.transfer_details'].\
            with_context(self.picking.do_enter_transfer_details().get('context')).\
            create({'picking_id': self.picking.id})
        self.assertEqual(len(popup.item_ids), 1)
        popup.save_transfer()
        self.assertEqual(len(self.picking.pack_operation_ids), 1)
        self.assertEqual(self.picking.pack_operation_ids.product_qty, 30)
        self.assertTrue(self.picking.packing_details_saved)

        # Decreasing qty and then rereserve_pick
        self.picking.pack_operation_ids.product_qty = 10
        self.assertTrue(self.picking.packing_details_saved)
        self.picking.rereserve_pick()
        self.assertEqual(len(self.picking.pack_operation_ids), 1)
        self.assertEqual(self.picking.pack_operation_ids.product_qty, 10)

        # Increasing qty and then rereserve_pick
        self.picking.pack_operation_ids.product_qty = 50
        self.assertTrue(self.picking.packing_details_saved)
        self.picking.rereserve_pick()
        self.assertEqual(len(self.picking.pack_operation_ids), 1)
        self.assertEqual(self.picking.pack_operation_ids.product_qty, 50)

        ##############################################
        # Deleting packops
        ##############################################

        self.picking.delete_packops()
        self.assertFalse(self.picking.packing_details_saved)
        self.picking.force_assign()
        self.picking.do_prepare_partial()
        self.assertEqual(len(self.picking.pack_operation_ids), 1)
        self.assertEqual(self.picking.pack_operation_ids.product_qty, 30)

        # Decreasing qty and then rereserve_pick
        self.picking.pack_operation_ids.product_qty = 5
        self.assertFalse(self.picking.packing_details_saved)
        self.picking.rereserve_pick()
        self.assertEqual(len(self.picking.pack_operation_ids), 1)
        self.assertEqual(self.picking.pack_operation_ids.product_qty, 30)

        # Increasing qty and then rereserve_pick
        self.picking.pack_operation_ids.product_qty = 60
        self.assertFalse(self.picking.packing_details_saved)
        self.picking.rereserve_pick()
        self.assertEqual(len(self.picking.pack_operation_ids), 1)
        self.assertEqual(self.picking.pack_operation_ids.product_qty, 30)
