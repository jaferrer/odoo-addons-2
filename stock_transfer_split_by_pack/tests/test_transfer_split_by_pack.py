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

class TestStockTransferSplitByPack(common.TransactionCase):

    def setUp(self):
        super(TestStockTransferSplitByPack, self).setUp()
        self.picking1 = self.browse_ref("stock_transfer_split_by_pack.picking_to_stock")
        self.product_a1232 = self.browse_ref("product.product_product_6")
        self.location_shelf = self.browse_ref("stock.stock_location_components")
        self.location_stock = self.browse_ref("stock.stock_location_stock")
        self.product_uom_unit_id = self.ref("product.product_uom_unit")

    def test_10_split_by_pack_remaining(self):
        """Test splitting with remaining quantity and without packing."""
        self.picking1.action_confirm()
        self.picking1.action_assign()
        self.picking1.do_prepare_partial()
        wizard_id = self.picking1.do_enter_transfer_details()['res_id']
        wizard = self.env['stock.transfer_details'].browse(wizard_id)
        wizard_line = wizard.item_ids[0]
        split_popup = self.env['stock.transfer.split_by_pack'].with_context(active_id=wizard_line.id).create({
            'pack_qty': 40,
            'create_pack': False,
        })
        split_popup.with_context(active_id=wizard_line.id,active_model='stock.transfer_details_items').split_by_pack()
        self.assertEqual(len(wizard.item_ids), 8)
        for line in wizard.item_ids:
            if line == wizard_line:
                self.assertEqual(line.quantity, 20)
            else:
                self.assertEqual(line.quantity, 40)
            self.assertFalse(line.result_package_id)
        wizard.do_detailed_transfer()

    def test_20_split_by_pack_remaining_packs(self):
        """Test splitting with remaining quantity and packing."""
        self.picking1.action_confirm()
        self.picking1.action_assign()
        self.picking1.do_prepare_partial()
        wizard_id = self.picking1.do_enter_transfer_details()['res_id']
        wizard = self.env['stock.transfer_details'].browse(wizard_id)
        wizard_line = wizard.item_ids[0]
        split_popup = self.env['stock.transfer.split_by_pack'].with_context(active_id=wizard_line.id).create({
            'pack_qty': 40,
            'create_pack': True,
        })
        split_popup.with_context(active_id=wizard_line.id,active_model='stock.transfer_details_items').split_by_pack()
        self.assertEqual(len(wizard.item_ids), 8)
        packs = []
        for line in wizard.item_ids:
            if line == wizard_line:
                self.assertEqual(line.quantity, 20)
                self.assertFalse(line.result_package_id)
            else:
                self.assertEqual(line.quantity, 40)
                self.assertTrue(line.result_package_id)
                self.assertNotIn(line.result_package_id, packs)
            packs.append(line.result_package_id)
        wizard.do_detailed_transfer()

    def test_30_split_by_pack_all(self):
        """Test splitting without remaining quantity and without packing."""
        self.picking1.action_confirm()
        self.picking1.action_assign()
        self.picking1.do_prepare_partial()
        wizard_id = self.picking1.do_enter_transfer_details()['res_id']
        wizard = self.env['stock.transfer_details'].browse(wizard_id)
        wizard_line = wizard.item_ids[0]
        split_popup = self.env['stock.transfer.split_by_pack'].with_context(active_id=wizard_line.id).create({
            'pack_qty': 30,
            'create_pack': False,
        })
        split_popup.with_context(active_id=wizard_line.id,active_model='stock.transfer_details_items').split_by_pack()
        self.assertEqual(len(wizard.item_ids), 10)
        self.assertIn(wizard_line, wizard.item_ids)
        for line in wizard.item_ids:
            self.assertEqual(line.quantity, 30)
            self.assertFalse(line.result_package_id)
        wizard.do_detailed_transfer()

    def test_40_split_by_pack_all_packs(self):
        """Test splitting without remaining quantity and with packing."""
        self.picking1.action_confirm()
        self.picking1.action_assign()
        self.picking1.do_prepare_partial()
        wizard_id = self.picking1.do_enter_transfer_details()['res_id']
        wizard = self.env['stock.transfer_details'].browse(wizard_id)
        wizard_line = wizard.item_ids[0]
        split_popup = self.env['stock.transfer.split_by_pack'].with_context(active_id=wizard_line.id).create({
            'pack_qty': 30,
            'create_pack': True,
        })
        split_popup.with_context(active_id=wizard_line.id,active_model='stock.transfer_details_items').split_by_pack()
        self.assertEqual(len(wizard.item_ids), 10)
        self.assertIn(wizard_line, wizard.item_ids)
        packs = []
        for line in wizard.item_ids:
            self.assertEqual(line.quantity, 30)
            self.assertTrue(line.result_package_id)
            self.assertNotIn(line.result_package_id, packs)
            packs.append(line.result_package_id)
        wizard.do_detailed_transfer()

