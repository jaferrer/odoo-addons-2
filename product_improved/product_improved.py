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

import re

from openerp import models, api, _
from openerp.osv import expression


class ProductLabelProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            products = self.env['product.product']
            if operator in positive_operators:
                products = self.search([('default_code', operator, name)] + args, limit=limit)
                if not products:
                    products = self.search([('ean13', operator, name)] + args, limit=limit)
            if not products and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                products = self.search(args + [('default_code', operator, name)], limit=limit)
                if not limit or len(products) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    limit2 = (limit - len(products)) if limit else False
                    products |= self.search(args + [('name', operator, name),
                                                    ('id', 'not in', products.ids)], limit=limit2)
            elif not products and operator in expression.NEGATIVE_TERM_OPERATORS:
                products = self.search(args + ['&', '|', ('default_code', operator, name), (
                    'default_code', '=', False), ('name', operator, name)], limit=limit)
            if not products and operator in positive_operators:
                ptrn = re.compile(r'(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    products = self.search([('default_code', operator, res.group(2))] + args, limit=limit)
        else:
            products = self.search(args, limit=limit)
        result = products.name_get()
        return result

    @api.multi
    def open_moves_for_product(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx['search_default_done'] = True
        ctx['search_default_product_id'] = self.id
        ctx['default_product_id'] = self.id
        return {
            'name': _("Moves for product %s") % self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.move',
            'domain': ['|', ('location_id.company_id', '=', False),
                       ('location_id.company_id', 'child_of', self.env.user.company_id.id),
                       '|', ('location_dest_id.company_id', '=', False),
                       ('location_dest_id.company_id', 'child_of', self.env.user.company_id.id)],
            'context': ctx,
        }
