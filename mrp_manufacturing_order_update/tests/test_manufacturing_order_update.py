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
from datetime import *
from openerp.tests import common
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class TestOrderUpdate(common.TransactionCase):

    def setUp(self):
        super(TestOrderUpdate, self).setUp()

    def test_10_order_quantity_calculation(self):
        company = self.browse_ref('base.main_company')
        product_to_manufacture1 = self.browse_ref('mrp_manufacturing_order_update.product_to_manufacture1')
        unit = self.browse_ref('product.product_uom_unit')
        location1 = self.browse_ref('stock.stock_location_stock')
        bom1 = self.browse_ref('mrp_manufacturing_order_update.bom1')
        self.assertTrue(bom1.bom_line_ids)
        line1 = self.browse_ref('mrp_manufacturing_order_update.line1')
        line2 = self.browse_ref('mrp_manufacturing_order_update.line2')
        line3 = self.browse_ref('mrp_manufacturing_order_update.line3')
        line4 = self.browse_ref('mrp_manufacturing_order_update.line4')
        line5 = self.browse_ref('mrp_manufacturing_order_update.line5')
        line6 = self.browse_ref('mrp_manufacturing_order_update.line6')
        product1 = self.browse_ref('mrp_manufacturing_order_update.product1')
        product2 = self.browse_ref('mrp_manufacturing_order_update.product2')
        product3 = self.browse_ref('mrp_manufacturing_order_update.product3')

        mrp_production1 = self.env['mrp.production'].create({
            'name': 'mrp_production1',
            'product_id': product_to_manufacture1.id,
            'product_qty': 1,
            'product_uom': unit.id,
            'location_src_id': location1.id,
            'location_dest_id': location1.id,
            'date_planned': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'bom_id': bom1.id,
            'company_id': company.id,
        })

        mrp_production1.action_confirm()

        mrp_production2 = self.env['mrp.production'].create({
            'name': 'mrp_production2',
            'product_id': product_to_manufacture1.id,
            'product_qty': 1,
            'product_uom': unit.id,
            'location_src_id': location1.id,
            'location_dest_id': location1.id,
            'date_planned': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'bom_id': bom1.id,
            'company_id': company.id,
        })

        mrp_production2.action_confirm()
        self.assertTrue(mrp_production2.product_lines)

        # definition of function test_quantities to check that move_lines is matching the needs of product_lines

        def test_quantity(product, mrp_production):
            self.assertTrue(product in [x.product_id for x in mrp_production.product_lines])
            needed_qty = sum([y.product_qty for y in mrp_production.product_lines if y.product_id == product])
            ordered_qty = sum([z.product_qty for z in mrp_production.move_lines if z.product_id == product and z.state != 'cancel'])
            self.assertEqual(needed_qty, ordered_qty)

        def test_quantities(mrp_production):
            list_products_needed = []
            for item in mrp_production.product_lines:
                if item.product_id not in list_products_needed:
                    list_products_needed += [item.product_id]
            for product in list_products_needed:
                test_quantity(product, mrp_production)
            for item in mrp_production.move_lines:
                self.assertIn(item.product_id, list_products_needed)

        # test of function button_update

        def test_update(list_qty_to_change, list_line_to_delete, list_line_to_add):
            for item in list_qty_to_change:
                item[0].product_qty = item[1]
            for item in list_line_to_delete:
                item.unlink()
            for dict in list_line_to_add:
                dict['product_uom'] = unit.id
                dict['bom_id'] =  bom1.id
                self.env['mrp.bom.line'].create(dict)
            mrp_production1.button_update()
            test_quantities(mrp_production1)

        test_update([[line1, 10]], [], []) # increase one quantity
        test_update([[line1, 15], [line2, 15], [line4, 25], [line5, 30]], [], []) # increase two different quantities for two different product
        test_update([[line2, 5]], [], []) # decrease one quantity with one move to cancel
        test_update([[line3, 1], [line6, 5]], [], []) # decrease two quantities with two moves to cancel
        test_update([[line1, 5], [line2, 10], [line4, 20], [line5, 25]], [], []) # decrease two different quantities for two different product, one move for each to delete
        test_update([[line1, 1], [line2, 1], [line4, 1], [line5, 1]], [], []) # decrease two different quantities for two different product, two moves for each to delete
        test_update([[line1, 5], [line2, 10], [line4, 20], [line5, 25]], [], []) # back to first quantities
        test_update([[line1, 10], [line2, 9], [line4, 25], [line5, 24]], [], []) # for each product 1&2, one quantity decreases, the other one increases, new need superior to first need
        test_update([[line1, 11], [line2, 1], [line4, 1], [line5, 25]], [], []) # for each product 1&2, one quantity decreases, the other one increases, new need inferior to first need, several moves to delete for each
        test_update([], [line1], []) # deletion of one line
        test_update([], [line2, line3], []) # deletion of two lines
        new_line0 = {'product_id': product1.id, 'product_qty': 5}
        test_update([], [], [new_line0]) # creation of one line
        new_line1 = {'product_id': product2.id, 'product_qty': 10}
        new_line2 = {'product_id': product3.id, 'product_qty': 15}
        test_update([], [], [new_line1, new_line2]) # creation of two lines
        test_update([[line4, 100], [line6, 1]], [line5], [new_line1, new_line2]) #everything together : one quantity increase, another decrease, a line is deleted and two others created

        # testing modifications of field product_lines (function write from model mrp.production)
        # afterwards, function used tu update moves is the same as before: useless to test it again

        for item in mrp_production2.product_lines:
            if item.product_qty == 5:
                l1 = item.id
            if item.product_qty == 10:
                l2 = item.id
            if item.product_qty == 15:
                l3 = item.id
            if item.product_qty == 20:
                l4 = item.id
            if item.product_qty == 25:
                l5 = item.id
            if item.product_qty == 30:
                l6 = item.id
        self.assertTrue(l1)
        self.assertTrue(l2)
        self.assertTrue(l3)
        self.assertTrue(l4)
        self.assertTrue(l5)
        self.assertTrue(l6)

        # changing a line quantity
        vals = {'product_lines': [[1, l1, {'product_qty': 10}], [4, l2, False], [4, l3, False], [4, l4, False], [4, l5, False], [4, l6, False]]}
        mrp_production2.write(vals)
        test_quantities(mrp_production2)

        # deleting a line :
        vals = {'product_lines': [[4, l1, False], [4, l2, False], [4, l3, False], [4, l4, False], [4, l5, False], [2, l6, False]]}
        mrp_production2.write(vals)
        test_quantities(mrp_production2)

        # adding a line
        vals = {'product_lines': [[4, l1, False], [4, l2, False], [4, l3, False], [4, l4, False], [4, l5, False], [0, False, {'product_uos_qty': 0, 'name': 'a', 'product_uom': 1, 'product_qty': 10, 'product_uos': False, 'product_id': product2.id}]]}
        mrp_production2.write(vals)
        test_quantities(mrp_production2)