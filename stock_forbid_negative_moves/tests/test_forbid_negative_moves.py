# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from openerp import exceptions


class TestForbidNegativeMove(common.TransactionCase):

    def setUp(self):
        super(TestForbidNegativeMove, self).setUp()
        self.product = self.browse_ref("product.product_product_6")
        self.location = self.browse_ref('stock.stock_location_suppliers')

    def test_10_forbid_negative_moves(self):
        with self.assertRaises(exceptions.except_orm):
            self.env['stock.move'].create({
                'name': u"Test move (Forbid Negative Move)",
                'product_id': self.product.id,
                'location_id': self.location.id,
                'location_dest_id': self.location.id,
                'product_uom_qty': -1,
                'product_uom': self.product.uom_id.id,
            })
