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

from odoo import models, api, _


class ProductPutawayStockLocation(models.Model):
    _inherit = "stock.location"

    @api.multi
    def get_putaway_strategy(self, product):
        """ Returns the location where the product has to be put, if any compliant putaway strategy is found.
        Otherwise returns None.
        """
        self.ensure_one()
        return super(ProductPutawayStockLocation,
                     self.with_context(putaway_location_id=self.id)).get_putaway_strategy(product)


class ProductPutawayLastStrategy(models.Model):
    _inherit = 'product.putaway'

    @api.model
    def _get_putaway_options(self):
        res = super(ProductPutawayLastStrategy, self)._get_putaway_options()
        res.append(('last', _(u"Last bin location")))
        return res

    @api.multi
    def _putaway_apply_last(self, product):
        quants = self.env["stock.quant"].search([
            ('product_id', '=', product.id),
            ('location_id', 'child_of', self.env.context.get('putaway_location_id'))
        ], order='in_date DESC, id desc', limit=1)

        return quants.location_id.id
