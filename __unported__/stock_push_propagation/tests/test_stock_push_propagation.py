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

class TestStockPushPropagation(common.TransactionCase):

    def setUp(self):
        super(TestStockPushPropagation, self).setUp()
        self.product_a1232 = self.browse_ref("product.product_product_6")
        self.location_shelf = self.browse_ref("stock.stock_location_components")
        self.location_1 = self.browse_ref("stock_push_propagation.stock_location_a")
        self.location_2 = self.browse_ref("stock_push_propagation.stock_location_b")
        self.push_rule = self.browse_ref("stock_push_propagation.propagate_location_path")
        self.product_uom_unit_id = self.ref("product.product_uom_unit")
        self.picking_type_id = self.ref("stock.picking_type_internal")

    def test_10_no_propagate(self):
        """Test push rule with default setting: no propagation."""
        self.product_a1232.route_ids = [(4, self.ref("stock_push_propagation.test_route"))]
        group = self.env['procurement.group'].create({
            'name': "Test group",
        })
        move = self.env["stock.move"].create({
            'name': "Test Push Propagate",
            'product_id': self.product_a1232.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 12,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location_1.id,
            'picking_type_id': self.picking_type_id,
            'group_id': group.id,
        })
        move.action_confirm()
        moves = self.env['stock.move'].search([('location_id','=',self.location_1.id),
                                               ('product_id','=',self.product_a1232.id)])
        self.assertEqual(len(moves), 1)
        self.assertFalse(moves[0].group_id)

    def test_20_propagate(self):
        """Test push rule with propagation."""
        self.push_rule.group_propagation_option = 'propagate'
        self.product_a1232.route_ids = [(4, self.ref("stock_push_propagation.test_route"))]
        group = self.env['procurement.group'].create({
            'name': "Test group",
        })
        move = self.env["stock.move"].create({
            'name': "Test Push Propagate",
            'product_id': self.product_a1232.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 12,
            'location_id': self.location_shelf.id,
            'location_dest_id': self.location_1.id,
            'picking_type_id': self.picking_type_id,
            'group_id': group.id,
        })
        move.action_confirm()
        moves = self.env['stock.move'].search([('location_id','=',self.location_1.id),
                                               ('product_id','=',self.product_a1232.id)])
        self.assertEqual(len(moves), 1)
        self.assertEqual(moves[0].group_id, group)
