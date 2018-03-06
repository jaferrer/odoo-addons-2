# -*- coding: utf8 -*-
#
#    Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from openerp.addons.product.tests import test_uom


class TestUom(test_uom.TestUom):

    def setUp(self):
        super(TestUom, self).setUp()

    def tests_same_uom(self):
        gram_id = self.ref('product.product_uom_gram')
        kg_id = self.ref('product.product_uom_kgm')

        qty = self.uom._compute_qty(self.env.cr, self.env.uid, gram_id, 1200, kg_id)
        self.assertEquals(qty, 1.2)

        qty = self.uom._compute_qty(self.env.cr, self.env.uid, gram_id, 1200.005, gram_id)
        self.assertEquals(qty, 1200.01)

        qty = self.uom._compute_qty(self.env.cr, self.env.uid, gram_id, 1200.005, gram_id, round=False)
        self.assertEquals(qty, 1200.005)
