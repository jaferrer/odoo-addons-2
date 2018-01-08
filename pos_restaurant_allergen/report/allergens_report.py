# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp.report import report_sxw
from openerp import _


class Parser(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_allergens': self.get_allergens,
        })

    def get_allergens(self):
        allergen_ids = self.pool.get('restaurant.allergen').search(self.cr, self.uid, [])
        allergens = self.pool.get('restaurant.allergen').browse(self.cr, self.uid, allergen_ids)
        result = {allergen: [] for allergen in allergens}
        sold_product_ids = self.pool.get('product.template').search(self.cr, self.uid,
                                                                    [('available_in_pos', '=', True)])
        sold_products = self.pool.get('product.template').browse(self.cr, self.uid, sold_product_ids)
        for product in sold_products:
            for allergen in product.manufactured_allergen_ids:
                result[allergen] += [product]
        return result
