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

from openerp.tests import common
from openerp.tools import float_compare


class TestFixNullQuants(common.TransactionCase):
    def setUp(self):
        super(TestFixNullQuants, self).setUp()
        self.test_product = self.browse_ref('fix_null_quants.test_product')
        self.test_quant = self.browse_ref('fix_null_quants.test_quant')

    def test_10_split_quasi_null_qty(self):
        self.assertEqual(self.test_product.uom_id.rounding, 0.001)
        qty = 0.0001
        self.assertEqual(float_compare(qty, 0, precision_rounding=self.test_product.uom_id.rounding), 0)
        quant = self.test_quant._quant_split(self.test_quant, qty)
        self.assertEqual(quant, self.test_quant)
        self.assertEqual(self.test_quant.qty, 10)

    def test_20_split_quasi_entire_quant(self):
        self.assertEqual(self.test_product.uom_id.rounding, 0.001)
        qty = 10.0001
        self.assertEqual(float_compare(qty, self.test_quant.qty,
                                       precision_rounding=self.test_product.uom_id.rounding), 0)
        quant = self.test_quant._quant_split(self.test_quant, qty)
        self.assertFalse(quant)
        self.assertEqual(self.test_quant.qty, 10)
