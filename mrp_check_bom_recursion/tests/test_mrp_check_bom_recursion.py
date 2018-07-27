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

from openerp import exceptions
from openerp.tests import common


class TestOrderUpdate(common.TransactionCase):

    def setUp(self):
        super(TestOrderUpdate, self).setUp()

        self.company = self.browse_ref('base.main_company')
        self.product_to_manufacture1 = self.browse_ref('mrp_check_bom_recursion.product_to_manufacture1')
        self.unit = self.browse_ref('product.product_uom_unit')
        self.location1 = self.browse_ref('stock.stock_location_stock')
        self.bom1 = self.browse_ref('mrp_check_bom_recursion.bom1')
        self.assertTrue(self.bom1.bom_line_ids)
        self.line1 = self.browse_ref('mrp_check_bom_recursion.line1')
        self.line2 = self.browse_ref('mrp_check_bom_recursion.line2')
        self.line3 = self.browse_ref('mrp_check_bom_recursion.line3')
        self.line4 = self.browse_ref('mrp_check_bom_recursion.line4')
        self.line5 = self.browse_ref('mrp_check_bom_recursion.line5')
        self.line6 = self.browse_ref('mrp_check_bom_recursion.line6')
        self.product1 = self.browse_ref('mrp_check_bom_recursion.product1')
        self.product2 = self.browse_ref('mrp_check_bom_recursion.product2')
        self.product3 = self.browse_ref('mrp_check_bom_recursion.product3')

    def test_10_check_recursion(self):
        """Check that the _check_bom_recursion method works correctly"""
        self.bom1._check_bom_recursion()  # Should not raise
        bom2 = self.env['mrp.bom'].create({
            "name": "Test BOM 2",
            "type": 'normal',
            "product_id": self.product_to_manufacture1.id,
            "product_tmpl_id": self.product_to_manufacture1.product_tmpl_id.id,
            "product_qty": 1.0,
            "product_uom": self.unit.id,
            "product_efficiency": 1.0,
        })
        line1 = self.env['mrp.bom.line'].create({
            "type": 'normal',
            "product_id": self.product1.id,
            "product_qty": 2.0,
            "product_uom": self.unit.id,
            "product_efficiency": 1.0,
            "bom_id": bom2.id,
        })

        with self.assertRaises(exceptions.except_orm):
            self.env['mrp.bom.line'].create({
                "type": 'normal',
                "product_id": self.product_to_manufacture1.id,
                "product_qty": 3.0,
                "product_uom": self.unit.id,
                "product_efficiency": 1.0,
                "bom_id": bom2.id,
            })
        with self.assertRaises(exceptions.except_orm):
            line1.product_id = self.product_to_manufacture1

        bom3 = self.env['mrp.bom'].create({
            "name": "Test BOM 2",
            "type": 'normal',
            "product_id": self.product1.id,
            "product_tmpl_id": self.product1.product_tmpl_id.id,
            "product_qty": 1.0,
            "product_uom": self.unit.id,
            "product_efficiency": 1.0,
        })
        line2 = self.env['mrp.bom.line'].create({
            "type": 'normal',
            "product_id": self.product2.id,
            "product_qty": 3.0,
            "product_uom": self.unit.id,
            "product_efficiency": 1.0,
            "bom_id": bom3.id,
        })

        with self.assertRaises(exceptions.except_orm):
            self.env['mrp.bom.line'].create({
                "type": 'normal',
                "product_id": self.product_to_manufacture1.id,
                "product_qty": 2.0,
                "product_uom": self.unit.id,
                "product_efficiency": 1.0,
                "bom_id": bom3.id,
            })
        with self.assertRaises(exceptions.except_orm):
            line2.product_id = self.product_to_manufacture1
