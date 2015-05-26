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
        self.assertTrue(company)
        product_to_manufacture1 = self.browse_ref('manufacturing_order_update.product_to_manufacture1')
        self.assertTrue(product_to_manufacture1)
        unit = self.browse_ref('product.product_uom_unit')
        self.assertTrue(unit)
        location1 = self.browse_ref('stock.stock_location_stock')
        self.assertTrue(location1)
        location2 = self.browse_ref('stock.location_dispatch_zone')
        self.assertTrue(location2)
        location3 = self.browse_ref('stock.location_order')
        self.assertTrue(location3)
        product1 = self.browse_ref('manufacturing_order_update.product1')
        self.assertTrue(product1)
        product2 = self.browse_ref('manufacturing_order_update.product2')
        self.assertTrue(product2)
        product3 = self.browse_ref('manufacturing_order_update.product3')
        self.assertTrue(product3)
        bom1 = self.browse_ref('manufacturing_order_update.bom1')
        self.assertTrue(bom1)
        self.assertTrue(bom1.bom_line_ids)
        line1 = self.browse_ref('manufacturing_order_update.line1')
        self.assertTrue(line1)
        line2 = self.browse_ref('manufacturing_order_update.line2')
        self.assertTrue(line2)
        line3 = self.browse_ref('manufacturing_order_update.line3')
        self.assertTrue(line3)

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

        move1.force_assign()

        self.assertEquals(move1.state, 'assigned')