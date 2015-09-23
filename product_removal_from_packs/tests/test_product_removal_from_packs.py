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


class TestProductRemovalFromPacks(common.TransactionCase):

    def setUp(self):
        super(TestProductRemovalFromPacks, self).setUp()
        self.location1 = self.browse_ref("product_removal_from_packs.location1")
        self.product1 = self.browse_ref("product_removal_from_packs.product1")
        self.lot1 = self.browse_ref("product_removal_from_packs.lot1")
        self.quant1 = self.browse_ref("product_removal_from_packs.quant1")
        self.quant2 = self.browse_ref("product_removal_from_packs.quant2")

    def create_move_out_and_test(self, qty, list_quants):
        quants = self.env['stock.quant'].search([('location_id', '=', self.location1.id)])
        move_out = self.env['stock.move'].create({
            'name': 'Quant out',
            'product_id': self.product1.id,
            'product_uom': self.browse_ref('product.product_uom_unit').id,
            'product_uom_qty': qty,
            'location_id': self.location1.id,
            'location_dest_id': self.browse_ref('stock.stock_location_customers').id})
        move_out.action_done()
        self.assertEqual(move_out.state, 'done')
        quants = self.env['stock.quant'].search([('location_id', '=', self.location1.id)])
        self.assertEqual(len(quants), len(list_quants))
        for quant in quants:
            self.assertIn([quant.product_id, quant.lot_id, quant.qty], list_quants)


    def test_10_product_removal_from_packs(self):

        # Testing integer final values
        self.create_move_out_and_test(2.0, [[self.product1, self.lot1, 4.0],
                                            [self.product1, self.env['stock.production.lot'], 9.0]])

        # Testing float final values
        self.create_move_out_and_test(3.0, [[self.product1, self.lot1, 2.5],
                                            [self.product1, self.env['stock.production.lot'], 7.5]])

        # Testing one negative final values
        self.create_move_out_and_test(7, [[self.product1, self.lot1, -1.0],
                                          [self.product1, self.env['stock.production.lot'], 4.0]])

        # Testing two negative final values (from one positive and one negative)
        self.create_move_out_and_test(10, [[self.product1, self.lot1, -6.0],
                                           [self.product1, self.env['stock.production.lot'], -1.0]])

        # Testing two negative final values again (from two negatives)
        self.create_move_out_and_test(2, [[self.product1, self.lot1, -7.0],
                                          [self.product1, self.env['stock.production.lot'], -2.0]])