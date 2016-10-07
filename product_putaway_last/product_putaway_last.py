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

from openerp import fields, models, api, _


class product_putaway_stock_location(models.Model):
    _inherit = "stock.location"

    @api.model
    def get_putaway_strategy(self, location, product):
        ''' Returns the location where the product has to be put, if any compliant putaway strategy is found.
        Otherwise returns None.'''
        return super(product_putaway_stock_location,
                     self.with_context(putaway_location=location)).get_putaway_strategy(location, product)


class product_putway_last_strategy(models.Model):
    _inherit = 'product.putaway'

    @api.cr_uid_context
    def _get_putaway_options(self, cr, uid, context=None):
        res = super(product_putway_last_strategy, self)._get_putaway_options(cr, uid, context)
        res.append(('last', _("Last bin location")))
        return res

    method = fields.Selection(_get_putaway_options, "Method", required=True)

    @api.model
    def putaway_apply(self, putaway_strat, product):
        location = self.env.context.get("putaway_location")
        if putaway_strat.method == 'last' and location is not None:
            quants = self.env["stock.quant"].search([('product_id', '=', product.id),
                                                     ('location_id', 'child_of', location.id)],
                                                    order='in_date DESC, id desc', limit=1)
            if len(quants) == 1:
                return quants[0].location_id.id
        else:
            return super(product_putway_last_strategy, self).putaway_apply(putaway_strat, product)
