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

from openerp import models, api, fields
from openerp.tools import float_compare


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.model
    def _quants_get_order(self, location, product, quantity, domain=[], orderby='in_date'):
        """ Implementation of removal strategies
            If it can not reserve, it will return a tuple (None, qty)
        """
        domain += location and [('location_id', 'child_of', location.id)] or []
        domain += [('product_id', '=', product.id)]
        if self.env.context.get('force_company'):
            domain += [('company_id', '=', self.env.context.get('force_company'))]
        res = []
        offset = 0
        while float_compare(quantity, 0, precision_rounding=product.uom_id.rounding) > 0:
            quants = self.search(domain, order=orderby, limit=10, offset=offset)
            if not quants:
                res.append((None, quantity))
                break
            for quant in quants:
                rounding = product.uom_id.rounding
                if float_compare(quantity, abs(quant.qty), precision_rounding=rounding) >= 0:
                    res += [(quant, abs(quant.qty))]
                    quantity -= abs(quant.qty)
                elif float_compare(quantity, 0.0, precision_rounding=rounding) != 0:
                    res += [(quant, quantity)]
                    quantity = 0
                    break
            offset += 10
        return res


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    visible_for_all_companies = fields.Boolean(string="Visible for all companies")
