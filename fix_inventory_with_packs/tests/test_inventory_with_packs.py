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

class TestMailNoAutofollow(common.TransactionCase):

    def setUp(self):
        super(TestMailNoAutofollow, self).setUp()
        self.stock = self.browse_ref('stock.stock_location_stock')
        self.package1 = self.browse_ref('fix_inventory_with_packs.package1')
        self.package2 = self.browse_ref('fix_inventory_with_packs.package2')
        self.product = self.browse_ref('fix_inventory_with_packs.product')
        self.quant_without_package = self.browse_ref('fix_inventory_with_packs.quant_without_package')
        self.quant1 = self.browse_ref('fix_inventory_with_packs.quant1')
        self.quant2 = self.browse_ref('fix_inventory_with_packs.quant2')
        self.quant3 = self.browse_ref('fix_inventory_with_packs.quant3')
        self.inventory = self.browse_ref('fix_inventory_with_packs.inventory')
        self.inventory_location = self.browse_ref('stock.location_inventory')

    def test_10_inventory_with_packs(self):
        """
        Transferring a quant from a package to another in the same location using stock inventory.
        """
        self.inventory.prepare_inventory()
        self.inventory.line_ids.unlink()

        self.env['stock.inventory.line'].create({
            'inventory_id': self.inventory.id,
            'product_id': self.product.id,
            'location_id': self.stock.id,
            'package_id': self.package1.id,
            'product_qty': 0,
        })

        self.env['stock.inventory.line'].create({
            'inventory_id': self.inventory.id,
            'product_id': self.product.id,
            'location_id': self.stock.id,
            'package_id': self.package2.id,
            'product_qty': 30,
        })

        self.inventory.action_done()
        self.assertFalse(self.package1.quant_ids)
        self.assertEqual(self.quant_without_package.location_id, self.stock)
        self.assertEqual(self.quant_without_package.qty, 100)
        self.assertFalse(self.quant_without_package.package_id)
        self.assertEqual(self.quant1.location_id, self.inventory_location)
        self.assertEqual(self.quant2.location_id, self.stock)
        self.assertEqual(self.quant3.location_id, self.stock)
        self.assertEqual(len(self.package2.quant_ids), 3)
        self.assertIn(self.quant2, self.package2.quant_ids)
        self.assertIn(self.quant3, self.package2.quant_ids)
        self.assertEqual(self.quant2.qty, 5)
        self.assertEqual(self.quant3.qty, 15)
        new_quant = self.package2.quant_ids.filtered(lambda quant: quant not in [self.quant2, self.quant3])
        self.assertTrue(new_quant)
        self.assertEqual(new_quant.location_id, self.stock)
        self.assertEqual(new_quant.product_id, self.product)
        self.assertEqual(new_quant.qty, 10)
