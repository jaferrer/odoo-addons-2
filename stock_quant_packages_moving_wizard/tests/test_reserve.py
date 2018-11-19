# -*- coding: utf8 -*-
#
# Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class TestWizard(common.TransactionCase):
    def setUp(self):
        super(TestWizard, self).setUp()

        self.product_c = self.browse_ref("stock_quant_packages_moving_wizard.product_c")
        self.stock = self.browse_ref("stock.stock_location_stock")
        self.location_source = self.browse_ref("stock_quant_packages_moving_wizard.stock_location_source")
        self.location_dest = self.browse_ref("stock_quant_packages_moving_wizard.stock_location_dest")
        self.location_dest_shelf = self.browse_ref("stock_quant_packages_moving_wizard.stock_location_dest_shelf")
        self.picking_type = self.browse_ref("stock.picking_type_internal")
        self.uom_couple = self.browse_ref('stock_quant_packages_moving_wizard.uom_couple')
        self.unit = self.browse_ref('product.product_uom_unit')

        self.supplier = self.browse_ref('stock.stock_location_suppliers')
        self.product1_auto_move = self.browse_ref('stock_quant_packages_moving_wizard.product1')
        self.product2_auto_move = self.browse_ref('stock_quant_packages_moving_wizard.product2')
        self.location_1 = self.browse_ref("stock_quant_packages_moving_wizard.stock_location_a")
        self.location_2 = self.browse_ref("stock_quant_packages_moving_wizard.stock_location_b")
        self.inventory_location = self.browse_ref('stock.location_inventory')

        self.env['stock.location']._parent_store_compute()
        self.env['stock.quant.package']._parent_store_compute()

    def test_10_move_quant_lines(self):
        self.env['stock.quant'].create({
            'product_id': self.product_c.id,
            'location_id': self.location_source.id,
            'qty': 50,
        })
        move1 = self.env['stock.move'].create({
            'name': "Move 1",
            'product_id': self.product_c.id,
            'location_id': self.location_source.id,
            'location_dest_id': self.location_dest.id,
            'product_uom': self.unit.id,
            'picking_type_id': self.picking_type.id,
            'product_uom_qty': 25,
            'date': '2018-10-6',
            'priority': '0',
        })
        move2 = self.env['stock.move'].create({
            'name': "Move 2",
            'product_id': self.product_c.id,
            'location_id': self.location_source.id,
            'location_dest_id': self.location_dest.id,
            'product_uom': self.unit.id,
            'picking_type_id': self.picking_type.id,
            'product_uom_qty': 15,
            'date': '2018-10-6',
            'priority': '1',
        })
        move3 = self.env['stock.move'].create({
            'name': "Move 3",
            'product_id': self.product_c.id,
            'location_id': self.location_source.id,
            'location_dest_id': self.location_dest.id,
            'product_uom': self.unit.id,
            'picking_type_id': self.picking_type.id,
            'product_uom_qty': 10,
            'date': '2018-10-6',
            'priority': '2',
        })
        move1.action_confirm()
        move2.action_confirm()
        move3.action_confirm()
        original_picking = move1.picking_id
        original_picking.ensure_one()
        self.assertEqual(move2.picking_id, original_picking)
        self.assertEqual(move3.picking_id, original_picking)
        original_picking.action_assign()
        self.assertEqual(original_picking.state, 'assigned')
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(move2.state, 'assigned')
        self.assertEqual(move3.state, 'assigned')
        quant1 = move1.reserved_quant_ids
        quant2 = move2.reserved_quant_ids
        quant3 = move3.reserved_quant_ids
        quant1.ensure_one()
        quant2.ensure_one()
        quant3.ensure_one()
        line = self.env['stock.product.line'].search([('product_id', '=', self.product_c.id)])
        line.ensure_one()
        self.assertEqual(line.qty, 50)
        wizard = self.env['product.move.wizard']. \
            with_context(active_ids=line.ids).create({
            'global_dest_loc': self.location_dest.id,
            'picking_type_id': self.picking_type.id,
            'is_manual_op': True
        })
        wizard.quant_line_ids.ensure_one().qty = 8
        picking_id = wizard.move_products()['res_id']
        picking = self.env['stock.picking'].browse(picking_id)
        self.assertEqual(picking.state, 'assigned')
        # Move used should be move 1 (move with highest priority)
        self.assertEqual(picking.move_lines, move1)

        # Move 1 should have taken a part on quant3 (smallest quant available)
        self.assertEqual(move1.product_qty, 8)
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(move1.reserved_quant_ids, quant3)
        self.assertEqual(quant3.qty, 8)

        # Move 2 should not have changed, as well as quant2
        self.assertEqual(move2.product_qty, 15)
        self.assertEqual(move2.state, 'assigned')
        self.assertEqual(move2.reserved_quant_ids, quant2)
        self.assertEqual(quant2.qty, 15)

        # Splitted quant should be alone
        splitted_quant = self.env['stock.quant'].search([('product_id', '=', self.product_c.id),
                                                         ('location_id', '=', self.location_source.id),
                                                         ('qty', '=', 2),
                                                         ('reservation_id', '=', False)])
        splitted_quant.ensure_one()

        # Move 3 should have been unreserved
        self.assertEqual(move3.product_qty, 10)
        self.assertEqual(move3.state, 'confirmed')
        self.assertFalse(move3.reserved_quant_ids)

        # Quant 2 should be alone.
        self.assertEqual(quant1.qty, 25)
        self.assertFalse(quant1.reservation_id)
