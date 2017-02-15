# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class TestStockPushPropagation(common.TransactionCase):
    def setUp(self):
        super(TestStockPushPropagation, self).setUp()
        self.product = self.browse_ref('stock_reservation_priority.product')
        self.quant1 = self.browse_ref('stock_reservation_priority.quant1')
        self.quant2 = self.browse_ref('stock_reservation_priority.quant2')
        self.move1 = self.browse_ref('stock_reservation_priority.move1')
        self.move2 = self.browse_ref('stock_reservation_priority.move2')
        self.move3 = self.browse_ref('stock_reservation_priority.move3')
        self.stock = self.browse_ref('stock.stock_location_stock')
        self.stock_child = self.browse_ref('stock_reservation_priority.stock_child')
        self.customers = self.browse_ref('stock.stock_location_customers')
        self.unit = self.browse_ref('product.product_uom_unit')

    def create_move_and_test(self, move_priority, move_qty, move_date, dict1, dict2, dict3, dict4, location=False,
                             skip_moves_assignation=False):
        if not skip_moves_assignation:
            self.move1.action_confirm()
            self.move2.action_confirm()
            self.move3.action_confirm()
            self.move1.action_assign()
            self.move2.action_assign()
            self.move3.action_assign()
            self.assertEqual(self.move1.state, 'assigned')
            self.assertEqual(self.move2.state, 'assigned')
            self.assertEqual(self.move3.state, 'assigned')
        new_move = self.env['stock.move'].create({
            'name': "New move to assign",
            'priority': move_priority,
            'product_uom': self.unit.id,
            'product_uom_qty': move_qty,
            'date': move_date,
            'product_id': self.product.id,
            'location_id': location and location.id or self.stock.id,
            'location_dest_id': self.customers.id,
        })
        new_move.action_confirm()
        new_move.action_assign()
        self.env['stock.move'].search([('product_id', '=', self.product.id),
                                       ('location_id', 'child_of', self.stock.id),
                                       ('state', 'not in', ['done', 'cancel'])]).action_assign()

        self.assertEqual(self.move1.state, dict1['state'])
        self.assertEqual(sum([quant.qty for quant in self.move1.reserved_quant_ids]), dict1['reserved_qty'])
        self.assertEqual(self.move2.state, dict2['state'])
        self.assertEqual(sum([quant.qty for quant in self.move2.reserved_quant_ids]), dict2['reserved_qty'])
        self.assertEqual(self.move3.state, dict3['state'])
        self.assertEqual(sum([quant.qty for quant in self.move3.reserved_quant_ids]), dict3['reserved_qty'])
        self.assertEqual(new_move.state, dict4['state'])
        self.assertEqual(sum([quant.qty for quant in new_move.reserved_quant_ids]), dict4['reserved_qty'])

    def test_01_stock_reservation_priority(self):
        self.create_move_and_test('0', 3, '2016-02-18 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 2},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'assigned', 'reserved_qty': 3})

    def test_02_stock_reservation_priority(self):
        self.create_move_and_test('0', 5, '2016-02-18 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'assigned', 'reserved_qty': 5})

    def test_03_stock_reservation_priority(self):
        self.create_move_and_test('0', 7, '2016-02-18 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'confirmed', 'reserved_qty': 5})

    def test_04_stock_reservation_priority(self):
        self.create_move_and_test('1', 3, '2016-02-18 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 2},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'assigned', 'reserved_qty': 3})

    def test_05_stock_reservation_priority(self):
        self.create_move_and_test('1', 5, '2016-02-18 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'assigned', 'reserved_qty': 5})

    def test_06_stock_reservation_priority(self):
        self.create_move_and_test('1', 10, '2016-02-18 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'confirmed', 'reserved_qty': 10},
                                  {'state': 'assigned', 'reserved_qty': 10})

    def test_07_stock_reservation_priority(self):
        self.create_move_and_test('1', 15, '2016-02-18 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'confirmed', 'reserved_qty': 5},
                                  {'state': 'assigned', 'reserved_qty': 15})

    def test_08_stock_reservation_priority(self):
        self.create_move_and_test('1', 20, '2016-02-18 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'assigned', 'reserved_qty': 20})

    def test_09_stock_reservation_priority(self):
        self.create_move_and_test('1', 25, '2016-02-18 12:00:00',
                                  {'state': 'confirmed', 'reserved_qty': 5},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'assigned', 'reserved_qty': 25})

    def test_10_stock_reservation_priority(self):
        self.create_move_and_test('0', 3, '2016-02-20 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 2},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'assigned', 'reserved_qty': 3})

    def test_11_stock_reservation_priority(self):
        self.create_move_and_test('0', 5, '2016-02-20 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'assigned', 'reserved_qty': 5})

    def test_12_stock_reservation_priority(self):
        self.create_move_and_test('0', 7, '2016-02-20 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'confirmed', 'reserved_qty': 5})

    def test_13_stock_reservation_priority(self):
        self.create_move_and_test('1', 3, '2016-02-20 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 2},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'assigned', 'reserved_qty': 3})

    def test_14_stock_reservation_priority(self):
        self.create_move_and_test('1', 5, '2016-02-20 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'assigned', 'reserved_qty': 5})

    def test_15_stock_reservation_priority(self):
        self.create_move_and_test('1', 10, '2016-02-20 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'confirmed', 'reserved_qty': 10},
                                  {'state': 'assigned', 'reserved_qty': 10})

    def test_16_stock_reservation_priority(self):
        self.create_move_and_test('1', 15, '2016-02-20 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'confirmed', 'reserved_qty': 5},
                                  {'state': 'assigned', 'reserved_qty': 15})

    def test_17_stock_reservation_priority(self):
        self.create_move_and_test('1', 20, '2016-02-20 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'assigned', 'reserved_qty': 20})

    def test_18_stock_reservation_priority(self):
        self.create_move_and_test('1', 25, '2016-02-20 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'confirmed', 'reserved_qty': 20})

    def test_19_stock_reservation_priority(self):
        self.create_move_and_test('0', 3, '2016-02-22 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'assigned', 'reserved_qty': 5},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'confirmed', 'reserved_qty': 0})

    def test_20_stock_reservation_priority(self):
        self.create_move_and_test('0', 5, '2016-02-22 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'assigned', 'reserved_qty': 5},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'confirmed', 'reserved_qty': 0})

    def test_21_stock_reservation_priority(self):
        self.create_move_and_test('0', 7, '2016-02-22 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'assigned', 'reserved_qty': 5},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'confirmed', 'reserved_qty': 0})

    def test_22_stock_reservation_priority(self):
        self.create_move_and_test('1', 3, '2016-02-22 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 2},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'assigned', 'reserved_qty': 3})

    def test_23_stock_reservation_priority(self):
        self.create_move_and_test('1', 5, '2016-02-22 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'assigned', 'reserved_qty': 5})

    def test_24_stock_reservation_priority(self):
        self.create_move_and_test('1', 10, '2016-02-22 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'confirmed', 'reserved_qty': 10},
                                  {'state': 'assigned', 'reserved_qty': 10})

    def test_25_stock_reservation_priority(self):
        self.create_move_and_test('1', 15, '2016-02-22 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'confirmed', 'reserved_qty': 5},
                                  {'state': 'assigned', 'reserved_qty': 15})

    def test_26_stock_reservation_priority(self):
        self.create_move_and_test('1', 20, '2016-02-22 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'assigned', 'reserved_qty': 20})

    def test_27_stock_reservation_priority(self):
        self.create_move_and_test('1', 25, '2016-02-22 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'confirmed', 'reserved_qty': 20})

    def test_28_stock_reservation_priority(self):
        self.create_move_and_test('2', 25, '2016-02-22 12:00:00',
                                  {'state': 'confirmed', 'reserved_qty': 5},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'assigned', 'reserved_qty': 25})

    def test_29_stock_reservation_priority(self):
        self.create_move_and_test('0', 3, '2016-02-23 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'assigned', 'reserved_qty': 5},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'confirmed', 'reserved_qty': 0})

    def test_30_stock_reservation_priority(self):
        self.create_move_and_test('0', 5, '2016-02-23 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'assigned', 'reserved_qty': 5},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'confirmed', 'reserved_qty': 0})

    def test_31_stock_reservation_priority(self):
        self.create_move_and_test('0', 7, '2016-02-23 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'assigned', 'reserved_qty': 5},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'confirmed', 'reserved_qty': 0})

    def test_32_stock_reservation_priority(self):
        self.create_move_and_test('1', 3, '2016-02-23 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 2},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'assigned', 'reserved_qty': 3})

    def test_33_stock_reservation_priority(self):
        self.create_move_and_test('1', 5, '2016-02-23 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'assigned', 'reserved_qty': 5})

    def test_34_stock_reservation_priority(self):
        self.create_move_and_test('1', 10, '2016-02-23 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'confirmed', 'reserved_qty': 5})

    def test_35_stock_reservation_priority(self):
        self.create_move_and_test('1', 15, '2016-02-23 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'confirmed', 'reserved_qty': 5})

    def test_36_stock_reservation_priority(self):
        self.create_move_and_test('1', 20, '2016-02-23 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'confirmed', 'reserved_qty': 5})

    def test_37_stock_reservation_priority(self):
        self.create_move_and_test('1', 25, '2016-02-23 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'assigned', 'reserved_qty': 15},
                                  {'state': 'confirmed', 'reserved_qty': 5})

    # Testing assignation of an outgoing move of a child location
    def test_38_stock_reservation_priority(self):
        self.create_move_and_test('1', 7, '2016-02-20 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'confirmed', 'reserved_qty': 13},
                                  {'state': 'assigned', 'reserved_qty': 7}, location=self.stock_child)

    def test_39_stock_reservation_priority(self):
        self.create_move_and_test('1', 12, '2016-02-20 12:00:00',
                                  {'state': 'assigned', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 0},
                                  {'state': 'confirmed', 'reserved_qty': 10},
                                  {'state': 'confirmed', 'reserved_qty': 10}, location=self.stock_child)

    # Testing unreservation of partially available moves
    def test_40_stock_reservation_priority(self):

        self.move1.action_confirm()
        self.move2.action_confirm()
        self.move3.action_confirm()
        self.quant1.quants_reserve([(self.quant2, 2)], self.move2)
        self.quant1.quants_reserve([(self.quant1, 15)], self.move3)
        self.assertEqual(self.move1.state, 'confirmed')
        self.assertEqual(self.move2.state, 'confirmed')
        self.assertEqual(self.move3.state, 'assigned')
        self.assertTrue(self.move2.partially_available)
        self.assertEqual(sum([quant.qty for quant in self.move2.reserved_quant_ids]), 2)
        self.assertEqual(sum([quant.qty for quant in self.move3.reserved_quant_ids]), 15)

        # We remove all the not reserved quants
        quants_to_remove = self.env['stock.quant'].search([('reservation_id', '=', False),
                                                           ('product_id', '=', self.product.id),
                                                           ('location_id', 'child_of', self.stock.id)])
        self.assertEqual(sum([quant.qty for quant in quants_to_remove]), 13)
        new_move = self.env['stock.move'].create({
            'name': "Outgoing move",
            'priority': '0',
            'product_uom': self.unit.id,
            'product_uom_qty': 13,
            'date': '2017-02-15 12:00:00',
            'product_id': self.product.id,
            'location_id': self.stock.id,
            'location_dest_id': self.customers.id,
        })
        new_move.action_confirm()
        new_move.action_assign()
        self.assertEqual(new_move.state, 'assigned')
        new_move.action_done()
        self.assertEqual(sum([quant.qty for quant in self.move2.reserved_quant_ids]), 2)
        self.assertEqual(sum([quant.qty for quant in self.move3.reserved_quant_ids]), 15)
        self.assertFalse(self.env['stock.quant'].search([('reservation_id', '=', False),
                                                           ('product_id', '=', self.product.id),
                                                           ('location_id', 'child_of', self.stock.id)]))

        self.create_move_and_test('2', 4, '2016-02-18 12:00:00',
                                      {'state': 'assigned', 'reserved_qty': 10},
                                      {'state': 'confirmed', 'reserved_qty': 0},
                                      {'state': 'confirmed', 'reserved_qty': 3},
                                      {'state': 'assigned', 'reserved_qty': 4}, skip_moves_assignation=True)
