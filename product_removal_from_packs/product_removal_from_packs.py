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

from openerp import api, models


class StockQuantRemovalFromPacks(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def apply_removal_strategy(self, location, product, qty, domain, removal_strategy):
        if removal_strategy == 'rss':
            list_removals = []
            quants = self.env['stock.quant'].search([('product_id', '=', product.id),
                                                     ('location_id', '=', location.id)])
            if quants:
                qty_to_remove_for_each_quant = float(qty) / len(quants)
                for quant in quants:
                    # Spliting quants which final qty should be negative. If not, they will be deleted by the system.
                    if quant.qty < qty_to_remove_for_each_quant:
                        nq = quant.copy({'qty': quant.qty - qty_to_remove_for_each_quant})
                        quant.qty = qty_to_remove_for_each_quant
                    list_removals += [(quant, qty_to_remove_for_each_quant)]
            return list_removals
        else:
            return super(StockQuantRemovalFromPacks, self).apply_removal_strategy(location, product, qty, domain, removal_strategy)
