# -*- coding: utf8 -*-
#
# Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class TestIncompleteProduction(common.TransactionCase):

    def create_quant(self, qty, package, lot, in_date, product, location):
        quant = self.env['stock.quant'].create({
            'qty': qty,
            'package_id': package and package.id or False,
            'lot_id': lot and lot.id or False,
            'in_date': in_date,
            'product_id': product.id,
            'location_id': location.id,
        })
        return quant

    def setUp(self):
        super(TestIncompleteProduction, self).setUp()
        self.product = self.browse_ref('pack_preference_for_moves_assignation.test_product')
        self.pack1 = self.browse_ref('pack_preference_for_moves_assignation.pack1')
        self.pack2 = self.browse_ref('pack_preference_for_moves_assignation.pack2')
        self.lot1 = self.browse_ref('pack_preference_for_moves_assignation.lot1')
        self.lot2 = self.browse_ref('pack_preference_for_moves_assignation.lot2')
        self.lot3 = self.browse_ref('pack_preference_for_moves_assignation.lot3')
        self.picking_type_out = self.browse_ref('stock.picking_type_out')
        self.unit = self.browse_ref('product.product_uom_unit')
        self.stock = self.browse_ref('stock.stock_location_stock')
        self.customer = self.browse_ref('stock.stock_location_customers')
        self.quant1 = self.create_quant(5, self.pack1, self.lot2, '2016-02-01 14:13:00', self.product, self.stock)
        self.quant2 = self.create_quant(10, self.pack1, self.lot1, '2016-02-01 14:13:00', self.product, self.stock)
        self.quant3 = self.create_quant(15, self.pack1, False, '2016-02-01 14:13:00', self.product, self.stock)
        self.quant4 = self.create_quant(20, self.pack2, False, '2016-02-03 14:13:00', self.product, self.stock)
        self.quant5 = self.create_quant(25, self.pack2, self.lot3, '2016-02-05 14:13:00', self.product, self.stock)
        self.quant6 = self.create_quant(30, self.pack2, False, '2016-02-05 14:13:00', self.product, self.stock)
        self.quant7 = self.create_quant(5, False, False, '2016-02-01 14:13:00', self.product, self.stock)
        self.quant8 = self.create_quant(10, False, False, '2016-02-03 14:13:00', self.product, self.stock)
        self.quant9 = self.create_quant(15, False, self.lot3, '2016-02-05 14:13:00', self.product, self.stock)
        print self.quant1, self.quant2, self.quant3, self.quant4, self.quant5
        print self.quant6, self.quant7, self.quant8, self.quant9

    def create_and_test(self, qty, list_reservations):
        picking = self.env['stock.picking'].create({
            'name': "Test picking (Pack Preference)",
            'picking_type_id': self.picking_type_out.id,
        })
        move = self.env['stock.move'].create({
            'name': "Test move (Pack Preference)",
            'picking_id': picking.id,
            'product_uom': self.unit.id,
            'location_id': self.stock.id,
            'location_dest_id': self.customer.id,
            'product_id': self.product.id,
            'product_uom_qty': qty,
        })
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(picking.state, 'assigned')
        self.assertEqual(picking.move_lines, move)
        self.assertEqual(len(list_reservations), len(move.reserved_quant_ids))
        for q in move.reserved_quant_ids:
            self.assertIn((q, q.qty), list_reservations)

    def test_01_pack_preference(self):
        self.create_and_test(1, [(self.quant2, 1)])

    def test_02_pack_preference(self):
        self.create_and_test(10, [(self.quant2, 10)])

    def test_03_pack_preference(self):
        self.create_and_test(11, [(self.quant2, 10), (self.quant1, 1)])

    def test_04_pack_preference(self):
        self.create_and_test(15, [(self.quant2, 10), (self.quant1, 5)])

    def test_05_pack_preference(self):
        self.create_and_test(16, [(self.quant2, 10), (self.quant1, 5), (self.quant3, 1)])

    def test_06_pack_preference(self):
        self.create_and_test(30, [(self.quant2, 10), (self.quant1, 5), (self.quant3, 15)])

    def test_07_pack_preference(self):
        self.create_and_test(31, [(self.quant2, 10), (self.quant1, 5), (self.quant3, 15), (self.quant7, 1)])

    def test_08_pack_preference(self):
        self.create_and_test(35, [(self.quant2, 10), (self.quant1, 5), (self.quant3, 15), (self.quant7, 5)])

    def test_09_pack_preference(self):
        self.create_and_test(36, [(self.quant2, 10), (self.quant1, 5), (self.quant3, 15), (self.quant7, 5),
                                  (self.quant4, 1)])

    def test_10_pack_preference(self):
        self.create_and_test(55, [(self.quant2, 10), (self.quant1, 5), (self.quant3, 15), (self.quant7, 5),
                                  (self.quant4, 20)])

    def test_11_pack_preference(self):
        self.create_and_test(56, [(self.quant2, 10), (self.quant1, 5), (self.quant3, 15), (self.quant7, 5),
                                  (self.quant4, 20), (self.quant8, 1)])

    def test_12_pack_preference(self):
        self.create_and_test(65, [(self.quant2, 10), (self.quant1, 5), (self.quant3, 15), (self.quant7, 5),
                                  (self.quant4, 20), (self.quant8, 10)])

    def test_13_pack_preference(self):
        self.create_and_test(66, [(self.quant2, 10), (self.quant1, 5), (self.quant7, 5), (self.quant4, 20),
                                  (self.quant8, 10), (self.quant3, 15), (self.quant5, 1)])

    def test_14_pack_preference(self):
        self.create_and_test(90, [(self.quant2, 10), (self.quant1, 5), (self.quant7, 5), (self.quant4, 20),
                                  (self.quant8, 10), (self.quant3, 15), (self.quant5, 25)])

    def test_15_pack_preference(self):
        self.create_and_test(91, [(self.quant2, 10), (self.quant1, 5), (self.quant7, 5), (self.quant4, 20),
                                  (self.quant8, 10), (self.quant3, 15), (self.quant5, 25), (self.quant6, 1)])

    def test_16_pack_preference(self):
        self.create_and_test(120, [(self.quant2, 10), (self.quant1, 5), (self.quant7, 5), (self.quant4, 20),
                                  (self.quant8, 10), (self.quant3, 15), (self.quant5, 25), (self.quant6, 30)])

    def test_17_pack_preference(self):
        self.create_and_test(121, [(self.quant2, 10), (self.quant1, 5), (self.quant7, 5), (self.quant4, 20),
                                  (self.quant8, 10), (self.quant3, 15), (self.quant5, 25), (self.quant6, 30),
                                   (self.quant9, 1)])

    def test_18_pack_preference(self):
        self.create_and_test(135, [(self.quant2, 10), (self.quant1, 5), (self.quant7, 5), (self.quant4, 20),
                                  (self.quant8, 10), (self.quant3, 15), (self.quant5, 25), (self.quant6, 30),
                                   (self.quant9, 15)])
