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
            pack_or_lot_or_reservation_domain = [x for x in domain if x[0] == 'package_id' or x[0] == 'lot_id' or
                                                 x[0] == 'reservation_id']
            domain += [('location_id', '=', location.id)] + pack_or_lot_or_reservation_domain
            for cond in pack_or_lot_or_reservation_domain:
                if cond[2]:
                    apply_rss = False
                    break
            if apply_rss:
                list_removals = []
                packs = self.env['stock.quant.package'].search([('location_id', '=', location.id)]).\
                    filtered(lambda p: product in [x.product_id for x in p.quant_ids])
                if packs:
                    qty_to_remove_for_each_pack = float(quantity) / len(packs)
                    for pack in packs:
                        qty_available_in_pack = sum([x.qty for x in pack.quant_ids if x.product_id == product])
                        if qty_available_in_pack >= qty_to_remove_for_each_pack:
                           list_removals += super(StockQuantRemovalFromPacks, self).\
                                apply_removal_strategy(location,product,qty_to_remove_for_each_pack,
                                                       domain + [('package_id', '=', pack.id)], 'fifo')
                        else:
                            for quant in pack.quant_ids:
                                if quant.product_id == product:
                                    list_removals += [(quant, quant.qty)]
                return list_removals
            else:
                return super(StockQuantRemovalFromPacks, self).apply_removal_strategy(location, product, quantity,
                                                                                      domain, 'fifo')
        return super(StockQuantRemovalFromPacks, self).apply_removal_strategy(location, product, quantity, domain,
                                                                              removal_strategy)
