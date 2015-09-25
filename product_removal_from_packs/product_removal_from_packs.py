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
    def apply_removal_strategy(self, location, product, quantity, domain, removal_strategy):
        if removal_strategy == 'rss':
            apply_rss = True
            pack_or_lot_or_reservation_domain = [x for x in domain if x[0] == 'package_id' or x[0] == 'lot_id' or x[0] == 'reservation_id']
            domain += [('location_id', '=', location.id)] + pack_or_lot_or_reservation_domain
            for cond in pack_or_lot_or_reservation_domain:
                if cond[2]:
                    apply_rss = False
                    break
            if apply_rss:
                list_removals = []
                quants = self.env['stock.quant'].search([('product_id', '=', product.id),
                                                         ('location_id', '=', location.id)])
                if quants:
                    qty_to_remove_for_each_quant = float(quantity) / len(quants)
                    for quant in quants:
                        if abs(quant.qty) <= qty_to_remove_for_each_quant:
                            # For positive quants which final quantity should be negative, we don't mind losing
                            # package_id and lot_id.
                            list_removals += [(None, qty_to_remove_for_each_quant - quant.qty)]
                        list_removals += [(quant, qty_to_remove_for_each_quant)]
                return list_removals
            else:
                removal_strategy = 'fifo'
        return super(StockQuantRemovalFromPacks, self).apply_removal_strategy(location, product, quantity, domain, removal_strategy)
