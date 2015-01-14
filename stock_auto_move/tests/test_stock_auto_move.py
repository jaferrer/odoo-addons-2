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

class TestStockAutoMove(common.TransactionCase):

    def setUp(self):
        super(TestStockAutoMove, self).setUp()
        self.product_a1232 = self.browse_ref("product.product_product_6")
        self.location_shelf = self.browse_ref("stock.stock_location_components")
        self.location_1 = self.browse_ref("stock_auto_move.stock_location_a")
        self.location_2 = self.browse_ref("stock_auto_move.stock_location_b")
        self.product_uom_unit_id = self.ref("product.product_uom_unit")

    def test_10_auto_move(self):
        """Check automatic processing of move with auto_move set."""
        move = self.env["stock.move"].create({
            'name': "Test Auto",
            'product_id': self.product_a1232.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 12,
            'location_id': self.location_1.id,
            'location_dest_id': self.location_2.id,
            'auto_move': True,
        })
        move2 = self.env["stock.move"].create({
            'name': "Test Manual",
            'product_id': self.product_a1232.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 3,
            'location_id': self.location_1.id,
            'location_dest_id': self.location_2.id,
            'auto_move': False,
        })
        move.action_confirm()
        move2.action_confirm()
        self.assertEqual(move.state, 'confirmed')
        self.assertEqual(move2.state, 'confirmed')
        move3 = self.env["stock.move"].create({
            'name': "Supply source location for test",
            'product_id': self.product_a1232.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 15,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location_1.id,
            'auto_move': False,
        })
        move3.action_confirm()
        move3.action_done()
        move.action_assign()
        move2.action_assign()
        self.assertEqual(move3.state, 'done')
        self.assertEqual(move2.state, 'assigned')
        self.assertEqual(move.state, 'done')

    def test_20_procurement_auto_move(self):
        """Check that move generated with procurement rule have auto_move set."""
        self.product_a1232.route_ids = [(4, self.ref("purchase.route_warehouse0_buy"))]
        proc = self.env["procurement.order"].create({
            'name': 'Test Procurement with auto_move',
            'date_planned': '2015-02-02 00:00:00',
            'product_id': self.product_a1232.id,
            'product_qty': 1,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_2.id,
        })
        proc.check()
        proc.run()
        self.assertEqual(proc.rule_id.id, self.ref("stock_auto_move.procurement_rule_a_to_b"))

        for move in proc.move_ids:
            self.assertEqual(move.auto_move, True)
            self.assertEqual(move.state, 'confirmed')
