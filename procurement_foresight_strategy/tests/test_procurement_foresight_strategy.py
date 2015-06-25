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
from datetime import datetime

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tests import common


class TestProcurementForesightStrategy(common.TransactionCase):

    def setUp(self):
        super(TestProcurementForesightStrategy, self).setUp()
        self.product_test = self.browse_ref("procurement_foresight_strategy.test_product")
        self.location_stock = self.browse_ref("stock.stock_location_stock")
        self.out_move_0 = self.browse_ref("procurement_foresight_strategy.outgoing_0")
        self.out_move_1 = self.browse_ref("procurement_foresight_strategy.outgoing_1")
        self.out_move_2 = self.browse_ref("procurement_foresight_strategy.outgoing_2")
        self.out_move_3 = self.browse_ref("procurement_foresight_strategy.outgoing_3")
        self.product_uom_unit_id = self.ref("product.product_uom_unit")

    def test_10_procurement_foresight(self):
        """Test foresight strategies."""
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'name': "Test OrderPoint",
            'product_id': self.product_test.id,
            'location_id': self.location_stock.id,
            'product_min_qty': 2,
            'product_max_qty': 0,
            'fill_strategy': "duration",
            'fill_duration': 5,
        })
        max_qty = orderpoint.get_max_qty(datetime.strptime("2015-02-20 12:34:56", DEFAULT_SERVER_DATETIME_FORMAT))
        self.assertEqual(max_qty, 12)
