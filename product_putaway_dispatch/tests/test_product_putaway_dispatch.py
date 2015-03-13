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

class TestProductPutawayWhereNeeded(common.TransactionCase):

    def setUp(self):
        super(TestProductPutawayWhereNeeded, self).setUp()
        self.picking1 = self.browse_ref("product_putaway_dispatch.picking_to_stock")
        self.picking2 = self.browse_ref("product_putaway_dispatch.picking_pack")
        self.product_a1232 = self.browse_ref("product.product_product_6")
        self.location_shelf = self.browse_ref("stock.stock_location_components")
        self.location_stock = self.browse_ref("product_putaway_dispatch.stock_location_stock")
        self.location_bin_1 = self.browse_ref("product_putaway_dispatch.stock_location_bin_1")
        self.location_bin_2 = self.browse_ref("product_putaway_dispatch.stock_location_bin_2")
        self.product_uom_unit_id = self.ref("product.product_uom_unit")
        # Confirm need moves
        self.need_moves = self.env['stock.move'].search([('location_id','in',[self.location_bin_1.id, self.location_bin_2.id]),
                                                    ('product_id','=',self.product_a1232.id)])
        self.need_moves.action_confirm()

    def test_10_simple_dispatch(self):
        """Test a simple dispatch without packs."""
        for move in self.need_moves:
            self.assertEqual(move.state, 'confirmed')
        self.picking1.action_confirm()
        self.picking1.action_assign()
        self.picking1.do_prepare_partial()
        wizard_id = self.picking1.do_enter_transfer_details()['res_id']
        wizard = self.env['stock.transfer_details'].browse(wizard_id)
        wizard.action_dispatch()
        wizard.do_detailed_transfer()
        self.assertEqual(self.picking1.state, 'done')
        quants_stock_1 = self.env["stock.quant"].search([('product_id','=',self.product_a1232.id),
                                                         ('location_id','=',self.location_bin_1.id)])
        quants_stock_2 = self.env["stock.quant"].search([('product_id','=',self.product_a1232.id),
                                                         ('location_id','=',self.location_bin_2.id)])
        self.assertGreaterEqual(len(quants_stock_1), 1)
        self.assertGreaterEqual(len(quants_stock_2), 1)
        qty_1 = sum([q.qty for q in quants_stock_1])
        self.assertEqual(qty_1, 8)
        qty_2 = sum([q.qty for q in quants_stock_2])
        self.assertEqual(qty_2, 12)

    def test_20_dispatch_with_package(self):
        """Test dispatch with a package to be taken."""
        # Create a package of 3 items on shelf
        pack = self.env['stock.quant.package'].create({'location_id': self.location_shelf.id})
        self.picking2.action_confirm()
        self.picking2.action_assign()
        self.picking2.do_prepare_partial()
        for pack_op in self.picking2.pack_operation_ids:
            pack_op.result_package_id = pack
            pack_op.in_date = "2015-02-01 00:00:00"
        self.picking2.do_transfer()
        # Go for the move itself
        self.picking1.action_confirm()
        self.picking1.action_assign()
        self.picking1.do_prepare_partial()
        wizard_id = self.picking1.do_enter_transfer_details()['res_id']
        wizard = self.env['stock.transfer_details'].browse(wizard_id)
        wizard.action_dispatch()
        wizard.do_detailed_transfer()
        self.assertEqual(self.picking1.state, 'done')
        quants_stock_1 = self.env["stock.quant"].search([('product_id','=',self.product_a1232.id),
                                                         ('location_id','=',self.location_bin_1.id)])
        quants_stock_2 = self.env["stock.quant"].search([('product_id','=',self.product_a1232.id),
                                                         ('location_id','=',self.location_bin_2.id)])
        self.assertGreaterEqual(len(quants_stock_1), 1)
        # Pack did not move
        self.assertEqual(pack.location_id, self.location_shelf)
        self.assertGreaterEqual(len(quants_stock_2), 1)
        qty_1 = sum([q.qty for q in quants_stock_1])
        self.assertEqual(qty_1, 8)
        qty_2 = sum([q.qty for q in quants_stock_2])
        self.assertEqual(qty_2, 12)

