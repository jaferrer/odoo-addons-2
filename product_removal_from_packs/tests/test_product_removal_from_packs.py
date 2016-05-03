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
from openerp import fields


class TestProductRemovalFromPacks(common.TransactionCase):

    def setUp(self):
        super(TestProductRemovalFromPacks, self).setUp()
        self.location1 = self.browse_ref("product_removal_from_packs.location1")
        self.product1 = self.browse_ref("product_removal_from_packs.product1")
        self.product2 = self.browse_ref("product_removal_from_packs.product2")
        self.product3 = self.browse_ref("product_removal_from_packs.product3")
        self.lot1 = self.browse_ref("product_removal_from_packs.lot1")
        self.lot2 = self.browse_ref("product_removal_from_packs.lot2")
        self.lot3 = self.browse_ref("product_removal_from_packs.lot3")
        self.package1 = self.browse_ref("product_removal_from_packs.package1")
        self.package2 = self.browse_ref("product_removal_from_packs.package2")
        self.quant9 = self.browse_ref("product_removal_from_packs.quant9")

    def create_move_out_and_test(self, qty, list_quants):
        move_out = self.env['stock.move'].create({
            'name': 'Quant out',
            'product_id': self.product1.id,
            'product_uom': self.browse_ref('product.product_uom_unit').id,
            'product_uom_qty': qty,
            'location_id': self.location1.id,
            'location_dest_id': self.browse_ref('stock.stock_location_customers').id,
            'picking_type_id': self.ref('stock.picking_type_internal')})
        move_out.action_confirm()
        self.assertTrue(move_out.picking_id)
        self.assertFalse(move_out.picking_id.pack_operation_ids)
        move_out.action_assign()
        move_out.picking_id.do_prepare_partial()
        move_out.picking_id.do_transfer()
        self.assertEqual(move_out.state, 'done')
        quants = self.env['stock.quant'].search([('location_id', '=', self.location1.id),
                                                 ('product_id', '=', self.product1.id)])
        self.assertEqual(len(quants), len(list_quants))
        for quant in quants:
            self.assertIn([quant.package_id, quant.lot_id, quant.qty], list_quants)

    def test_10_product_removal_from_packs(self):

        """
        Testing via moves.
        """

        if self.env['ir.module.module'].search([('name', '=', 'pack_preference_for_moves_assignation'),
                                                ('state', '=', 'installed')]):
            self.skipTest("Package preference for moves assignation module is installed")

        # Testing integer final values
        self.create_move_out_and_test(4.0, [[self.package1, self.lot1, 3.0],
                                            [self.package1, self.lot2, 10.0],
                                            [self.package2, self.env['stock.production.lot'], 23.0],
                                            [self.env['stock.quant.package'], self.env['stock.production.lot'], 15.0]])

        # Testing float final values
        self.create_move_out_and_test(1.0, [[self.package1, self.lot1, 3.0],
                                            [self.package1, self.lot2, 9.5],
                                            [self.package2, self.env['stock.production.lot'], 22.5],
                                            [self.env['stock.quant.package'], self.env['stock.production.lot'], 15.0]])

        # Testing one negative final value, losing a lot number.
        self.create_move_out_and_test(19.0, [[self.package1, self.lot2, 3.0],
                                            [self.package2, self.env['stock.production.lot'], 13.0],
                                            [self.env['stock.quant.package'], self.env['stock.production.lot'], 15.0]])

        # Trying to consume more than available, losing a package
        self.create_move_out_and_test(8.0, [[self.package2, self.env['stock.production.lot'], 9.0],
                                            [self.env['stock.quant.package'], self.env['stock.production.lot'], 14.0]])

        # Again, no more package
        self.create_move_out_and_test(10.0, [[self.env['stock.quant.package'], self.env['stock.production.lot'], 13.0]])

    def create_inventory_and_test(self, list_lines_to_create, list_quants):
        inventaire = self.env['stock.inventory'].create({
            'name': 'MAZ',
            'location_id': self.location1.id,
            'filter': 'partial',
            'date': fields.Datetime.now(),
            'company_id': self.browse_ref('base.main_company').id})
        inventaire.prepare_inventory()
        for line_data in list_lines_to_create:
            self.env['stock.inventory.line'].create({
                'inventory_id': inventaire.id,
                'product_id': line_data[0].id,
                'package_id': line_data[1] and line_data[1].id or False,
                'prod_lot_id': line_data[2] and line_data[2].id or False,
                'product_qty': line_data[3],
                'product_uom_id': self.browse_ref('product.product_uom_unit').id,
                'location_id': self.location1.id})
        inventaire.action_done()
        quants = self.env['stock.quant'].search([('location_id', '=', self.location1.id)])
        self.assertEqual(len(quants), len(list_quants))
        for quant in quants:
            self.assertIn([quant.package_id, quant.product_id, quant.lot_id, quant.qty], list_quants)

    def test_20_product_removal_from_packs(self):

        """
        Testing via stock inventories.
        """

        # We need a negative quant for this test
        self.quant9.qty = -15.0

        # Package and lot specified, simple case.
        self.create_inventory_and_test([[self.product2, self.package2, self.lot3, 60.0]],
                                       [[self.package1, self.product1, self.lot1, 5.0],
                                        [self.package1, self.product1, self.lot2, 10.0],
                                        [self.package1, self.product2, self.env['stock.production.lot'], 15.0],
                                        [self.package1, self.product3, self.env['stock.production.lot'], 20.0],
                                        [self.package2, self.product1, self.env['stock.production.lot'], 25.0],
                                        [self.package2, self.product2, self.lot3, -30.0],
                                        [self.package2, self.product2, self.lot3, 90.0],
                                        [self.package2, self.product2, self.env['stock.production.lot'], 35.0],
                                        [self.package2, self.product3, self.env['stock.production.lot'], -40.0],
                                        [self.env['stock.quant.package'], self.product1, self.env['stock.production.lot'], -15.0],
                                        [self.env['stock.quant.package'], self.product2, self.lot3, 50.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 55.0]])

        # Package and lot specified, two quants of same product with different lot numbers in package 1.
        self.create_inventory_and_test([[self.product1, self.package1, self.lot1, 3.0]],
                                       [[self.package1, self.product1, self.lot1, 3.0],
                                        [self.package1, self.product1, self.lot2, 10.0],
                                        [self.package1, self.product2, self.env['stock.production.lot'], 15.0],
                                        [self.package1, self.product3, self.env['stock.production.lot'], 20.0],
                                        [self.package2, self.product1, self.env['stock.production.lot'], 25.0],
                                        [self.package2, self.product2, self.lot3, -30.0],
                                        [self.package2, self.product2, self.lot3, 90.0],
                                        [self.package2, self.product2, self.env['stock.production.lot'], 35.0],
                                        [self.package2, self.product3, self.env['stock.production.lot'], -40.0],
                                        [self.env['stock.quant.package'], self.product1, self.env['stock.production.lot'], -15.0],
                                        [self.env['stock.quant.package'], self.product2, self.lot3, 50.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 55.0]])

        # No package and no lot, from a positive quant.
        self.create_inventory_and_test([[self.product3, False, False, 65]],
                                       [[self.package1, self.product1, self.lot1, 3.0],
                                        [self.package1, self.product1, self.lot2, 10.0],
                                        [self.package1, self.product2, self.env['stock.production.lot'], 15.0],
                                        [self.package1, self.product3, self.env['stock.production.lot'], 20.0],
                                        [self.package2, self.product1, self.env['stock.production.lot'], 25.0],
                                        [self.package2, self.product2, self.lot3, -30.0],
                                        [self.package2, self.product2, self.lot3, 90.0],
                                        [self.package2, self.product2, self.env['stock.production.lot'], 35.0],
                                        [self.package2, self.product3, self.env['stock.production.lot'], -40.0],
                                        [self.env['stock.quant.package'], self.product1, self.env['stock.production.lot'], -15.0],
                                        [self.env['stock.quant.package'], self.product2, self.lot3, 50.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 55.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 10.0]])

        # No package and no lot, from a negative quant.
        self.create_inventory_and_test([[self.product1, False, False, 10]],
                                       [[self.package1, self.product1, self.lot1, 3.0],
                                        [self.package1, self.product1, self.lot2, 10.0],
                                        [self.package1, self.product2, self.env['stock.production.lot'], 15.0],
                                        [self.package1, self.product3, self.env['stock.production.lot'], 20.0],
                                        [self.package2, self.product1, self.env['stock.production.lot'], 25.0],
                                        [self.package2, self.product2, self.lot3, -30.0],
                                        [self.package2, self.product2, self.lot3, 90.0],
                                        [self.package2, self.product2, self.env['stock.production.lot'], 35.0],
                                        [self.package2, self.product3, self.env['stock.production.lot'], -40.0],
                                        [self.env['stock.quant.package'], self.product1, self.env['stock.production.lot'], -15.0],
                                        [self.env['stock.quant.package'], self.product1, self.env['stock.production.lot'], 25.0],
                                        [self.env['stock.quant.package'], self.product2, self.lot3, 50.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 55.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 10.0]])

        # Package and no lot, one possibility
        self.create_inventory_and_test([[self.product2, self.package1, False, 10]],
                                       [[self.package1, self.product1, self.lot1, 3.0],
                                        [self.package1, self.product1, self.lot2, 10.0],
                                        [self.package1, self.product2, self.env['stock.production.lot'], 10.0],
                                        [self.package1, self.product3, self.env['stock.production.lot'], 20.0],
                                        [self.package2, self.product1, self.env['stock.production.lot'], 25.0],
                                        [self.package2, self.product2, self.lot3, -30.0],
                                        [self.package2, self.product2, self.lot3, 90.0],
                                        [self.package2, self.product2, self.env['stock.production.lot'], 35.0],
                                        [self.package2, self.product3, self.env['stock.production.lot'], -40.0],
                                        [self.env['stock.quant.package'], self.product1, self.env['stock.production.lot'], -15.0],
                                        [self.env['stock.quant.package'], self.product1, self.env['stock.production.lot'], 25.0],
                                        [self.env['stock.quant.package'], self.product2, self.lot3, 50.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 55.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 10.0]])

        # Package and no lot, one possibility.
        self.create_inventory_and_test([[self.product3, self.package1, False, 35]],
                                       [[self.package1, self.product1, self.lot1, 3.0],
                                        [self.package1, self.product1, self.lot2, 10.0],
                                        [self.package1, self.product2, self.env['stock.production.lot'], 10.0],
                                        [self.package1, self.product3, self.env['stock.production.lot'], 15.0],
                                        [self.package1, self.product3, self.env['stock.production.lot'], 20.0],
                                        [self.package2, self.product1, self.env['stock.production.lot'], 25.0],
                                        [self.package2, self.product2, self.lot3, -30.0],
                                        [self.package2, self.product2, self.lot3, 90.0],
                                        [self.package2, self.product2, self.env['stock.production.lot'], 35.0],
                                        [self.package2, self.product3, self.env['stock.production.lot'], -40.0],
                                        [self.env['stock.quant.package'], self.product1, self.env['stock.production.lot'], -15.0],
                                        [self.env['stock.quant.package'], self.product1, self.env['stock.production.lot'], 25.0],
                                        [self.env['stock.quant.package'], self.product2, self.lot3, 50.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 55.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 10.0]])

        # Package and no lot, two possibilities, decreasing quantity
        self.create_inventory_and_test([[self.product3, self.package1, False, 10]],
                                       [[self.package1, self.product1, self.lot1, 3.0],
                                        [self.package1, self.product1, self.lot2, 10.0],
                                        [self.package1, self.product2, self.env['stock.production.lot'], 10.0],
                                        [self.package1, self.product3, self.env['stock.production.lot'], 10.0],
                                        [self.package2, self.product1, self.env['stock.production.lot'], 25.0],
                                        [self.package2, self.product2, self.lot3, -30.0],
                                        [self.package2, self.product2, self.lot3, 90.0],
                                        [self.package2, self.product2, self.env['stock.production.lot'], 35.0],
                                        [self.package2, self.product3, self.env['stock.production.lot'], -40.0],
                                        [self.env['stock.quant.package'], self.product1, self.env['stock.production.lot'], -15.0],
                                        [self.env['stock.quant.package'], self.product1, self.env['stock.production.lot'], 25.0],
                                        [self.env['stock.quant.package'], self.product2, self.lot3, 50.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 55.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 10.0]])

        # Package and no lot, two possibilities, decreasing quantity
        self.create_inventory_and_test([[self.product3, self.package1, False, 35]],
                                       [[self.package1, self.product1, self.lot1, 3.0],
                                        [self.package1, self.product1, self.lot2, 10.0],
                                        [self.package1, self.product2, self.env['stock.production.lot'], 10.0],
                                        [self.package1, self.product3, self.env['stock.production.lot'], 10.0],
                                        [self.package1, self.product3, self.env['stock.production.lot'], 25.0],
                                        [self.package2, self.product1, self.env['stock.production.lot'], 25.0],
                                        [self.package2, self.product2, self.lot3, -30.0],
                                        [self.package2, self.product2, self.lot3, 90.0],
                                        [self.package2, self.product2, self.env['stock.production.lot'], 35.0],
                                        [self.package2, self.product3, self.env['stock.production.lot'], -40.0],
                                        [self.env['stock.quant.package'], self.product1, self.env['stock.production.lot'], -15.0],
                                        [self.env['stock.quant.package'], self.product1, self.env['stock.production.lot'], 25.0],
                                        [self.env['stock.quant.package'], self.product2, self.lot3, 50.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 55.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 10.0]])

        # Lot and no package, decreasing quantity
        self.create_inventory_and_test([[self.product2, False, self.lot3, 10]],
                                       [[self.package1, self.product1, self.lot1, 3.0],
                                        [self.package1, self.product1, self.lot2, 10.0],
                                        [self.package1, self.product2, self.env['stock.production.lot'], 10.0],
                                        [self.package1, self.product3, self.env['stock.production.lot'], 10.0],
                                        [self.package1, self.product3, self.env['stock.production.lot'], 25.0],
                                        [self.package2, self.product1, self.env['stock.production.lot'], 25.0],
                                        [self.package2, self.product2, self.lot3, -30.0],
                                        [self.package2, self.product2, self.lot3, 90.0],
                                        [self.package2, self.product2, self.env['stock.production.lot'], 35.0],
                                        [self.package2, self.product3, self.env['stock.production.lot'], -40.0],
                                        [self.env['stock.quant.package'], self.product1, self.env['stock.production.lot'], -15.0],
                                        [self.env['stock.quant.package'], self.product1, self.env['stock.production.lot'], 25.0],
                                        [self.env['stock.quant.package'], self.product2, self.lot3, 10.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 55.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 10.0]])

        # Lot and no package, increasing quantity
        self.create_inventory_and_test([[self.product2, False, self.lot3, 30]],
                                       [[self.package1, self.product1, self.lot1, 3.0],
                                        [self.package1, self.product1, self.lot2, 10.0],
                                        [self.package1, self.product2, self.env['stock.production.lot'], 10.0],
                                        [self.package1, self.product3, self.env['stock.production.lot'], 10.0],
                                        [self.package1, self.product3, self.env['stock.production.lot'], 25.0],
                                        [self.package2, self.product1, self.env['stock.production.lot'], 25.0],
                                        [self.package2, self.product2, self.lot3, -30.0],
                                        [self.package2, self.product2, self.lot3, 90.0],
                                        [self.package2, self.product2, self.env['stock.production.lot'], 35.0],
                                        [self.package2, self.product3, self.env['stock.production.lot'], -40.0],
                                        [self.env['stock.quant.package'], self.product1, self.env['stock.production.lot'], -15.0],
                                        [self.env['stock.quant.package'], self.product1, self.env['stock.production.lot'], 25.0],
                                        [self.env['stock.quant.package'], self.product2, self.lot3, 10.0],
                                        [self.env['stock.quant.package'], self.product2, self.lot3, 20.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 55.0],
                                        [self.env['stock.quant.package'], self.product3, self.env['stock.production.lot'], 10.0]])
