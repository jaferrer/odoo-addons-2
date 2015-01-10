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

class TestPackageWeight(common.TransactionCase):

    def setUp(self):
        super(TestPackageWeight, self).setUp()

    def test_weight_calculation(self):
        """Test of weight calculation."""
        product_10 = self.browse_ref('product.product_product_10')
        product_7 = self.browse_ref('product.product_product_7')
        product_9 = self.browse_ref('product.product_product_9')
        product_10.weight = 60
        product_10.weight_net = 55
        product_7.weight = 70
        product_7.weight_net = 65
        product_9.weight = 90
        product_9.weight_net = 85
        stock_id = self.ref('stock.stock_location_components')
        quant_10 = self.env['stock.quant'].search([('product_id','=',product_10.id),('location_id','=',stock_id)])
        quant_7 = self.env['stock.quant'].search([('product_id','=',product_7.id),('location_id','=',stock_id)])
        quant_9 = self.env['stock.quant'].search([('product_id','=',product_9.id),('location_id','=',stock_id)])
        pack_1 = self.env['stock.quant.package'].create({
            'name': "PACK01",
        })
        print str(quant_10)
        quant_10[0].package_id = pack_1.id
        quant_7[0].package_id = pack_1.id
        ul = self.browse_ref('product.product_ul_box')
        ul.weight = 7.0
        pack_2 = self.env['stock.quant.package'].create({
            'name': "PACK02",
            'ul_id': ul.id,
        })
        pack_1[0].parent_id = pack_2.id
        quant_9[0].package_id = pack_2.id

        # Pack 1 weight should be 8 * 60 + 18 * 70 = 1740
        self.assertEqual(pack_1.weight, 1740.0)
        # Pack 1 net weight should be 8 * 55 + 18 * 65 = 1610
        self.assertEqual(pack_1.weight_net, 1610.0)
        # Pack 2 weight should be 1740 + 22 * 90 + 7 = 3727
        self.assertEqual(pack_2.weight, 3727)
        # Pack 2 net weight should be 1610 + 22 * 85 = 3480
        self.assertEqual(pack_2.weight_net, 3480)
