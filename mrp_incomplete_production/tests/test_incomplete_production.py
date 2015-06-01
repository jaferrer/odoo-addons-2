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


class TestIncompleteProduction(common.TransactionCase):

    def setUp(self):
        super(TestIncompleteProduction, self).setUp()

    def test_10_incomplete_production(self):
        company = self.browse_ref('base.main_company')
        product_to_manufacture1 = self.browse_ref('mrp_incomplete_production.product_to_manufacture1')
        unit = self.browse_ref('product.product_uom_unit')
        location1 = self.browse_ref('stock.stock_location_stock')
        location2 = self.browse_ref('stock.location_dispatch_zone')
        location3 = self.browse_ref('stock.location_order')
        product1 = self.browse_ref('mrp_incomplete_production.product1')
        product2 = self.browse_ref('mrp_incomplete_production.product2')
        product3 = self.browse_ref('mrp_incomplete_production.product3')
        bom1 = self.browse_ref('mrp_incomplete_production.bom1')
        line1 = self.browse_ref('mrp_incomplete_production.line1')
        line2 = self.browse_ref('mrp_incomplete_production.line2')
        line3 = self.browse_ref('mrp_incomplete_production.line3')

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

        self.assertTrue(mrp_production1)
        mrp_production1.action_confirm()
        self.assertEquals(len(mrp_production1.move_lines), 3)

        for move in mrp_production1.move_lines:
            if move.product_qty == 5:
                move1 = move
            if move.product_qty == 10:
                move2 = move
            if move.product_qty == 15:
                move3 = move

        self.assertTrue(move1)
        self.assertTrue(move2)
        self.assertTrue(move3)

        # test with one move available: move1
        move1.force_assign()
        self.assertEquals(move1.state, 'assigned')

        mrp_product_produce1_data = {
            'production_id': mrp_production1.id,
            'consume_lines': mrp_production1._calculate_qty(mrp_production1, product_qty=0.0, context=None),
            'mode': lambda *x: 'consume_produce',
        }
        mrp_product_produce1 = self.env['mrp.product.produce'].create(mrp_product_produce1_data)
        # 3 fonctions de défaut déjà appelées à la création ?
        print mrp_product_produce1

        # mrp_production1.action_produce(mrp_production1.id, 1.0, 'consume_produce', wiz=False, context=None)
        # # mrp_production1.signal_workflow('act_mrp_product_produce')
        # print('================================================test==========================================================')
        # self.assertEquals(len(mrp_production1.move_lines2), 1)
        # self.assertEquals(mrp_production1.move_lines2.product_id, product1)
        # self.assertEquals(mrp_production1.move_lines2.product_qty, 5.0)
        # self.assertTrue(mrp_production1.state == 'done')
        #
        # self.assertTrue(mrp_production1.child_order_id)
        # child1 = mrp_production1.child_order_id
        # self.assertEquals(len(child1), 1)
        #
        # self.assertTrue(child1.backorder_id)
        # self.assertEquals(len(child1), 1)
        # print child1
        # for item in child1.move_lines:
        #     print item.product_id.name, item.product_qty
        # print [x.product_id.name for x in child1.move_lines]
        #
        # self.assertEquals(len(child1.move_lines), 2)
        # self.assertTrue(product2 in [x.product_id for x in child1.move_lines])
        # self.assertTrue(product3 in [x.product_id for x in child1.move_lines])

        # for item in


