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

from openerp.tools import float_round
from openerp.osv import osv
import openerp.addons.decimal_precision as dp


class StockLandedCostsFixed(osv.osv):
    _inherit = 'stock.landed.cost'

    def compute_landed_cost(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('stock.valuation.adjustment.lines')
        unlink_ids = line_obj.search(cr, uid, [('cost_id', 'in', ids)], context=context)
        line_obj.unlink(cr, uid, unlink_ids, context=context)
        digits = dp.get_precision('Product Price')(cr)
        towrite_dict = {}
        for cost in self.browse(cr, uid, ids, context=None):
            if not cost.picking_ids:
                continue
            picking_ids = [p.id for p in cost.picking_ids]
            total_qty = 0.0
            total_cost = 0.0
            total_weight = 0.0
            total_volume = 0.0
            total_line = 0.0
            vals = self.get_valuation_lines(cr, uid, [cost.id], picking_ids=picking_ids, context=context)
            for v in vals:
                for line in cost.cost_lines:
                    v.update({'cost_id': cost.id, 'cost_line_id': line.id})
                    self.pool.get('stock.valuation.adjustment.lines').create(cr, uid, v, context=context)
                total_qty += v.get('quantity', 0.0)
                total_cost += v.get('former_cost', 0.0)
                total_weight += v.get('weight', 0.0)
                total_volume += v.get('volume', 0.0)
                total_line += 1

            for line in cost.cost_lines:
                value_split = 0.0
                for valuation in cost.valuation_adjustment_lines:
                    value = 0.0
                    if valuation.cost_line_id and valuation.cost_line_id.id == line.id:
                        if line.split_method == 'by_quantity' and total_qty:
                            per_unit = (line.price_unit / total_qty)
                            value = valuation.quantity * per_unit
                        elif line.split_method == 'by_weight' and total_weight:
                            per_unit = (line.price_unit / total_weight)
                            value = valuation.weight * per_unit
                        elif line.split_method == 'by_volume' and total_volume:
                            per_unit = (line.price_unit / total_volume)
                            value = valuation.volume * per_unit
                        elif line.split_method == 'equal':
                            value = (line.price_unit / total_line)
                        elif line.split_method == 'by_current_cost_price' and total_cost:
                            per_unit = (line.price_unit / total_cost)
                            value = valuation.former_cost * per_unit
                        else:
                            value = (line.price_unit / total_line)

                        if digits:
                            value = float_round(value, precision_digits=digits[1], rounding_method='UP')
                            value = min(value, line.price_unit - value_split) if value > 0 else max(value, line.price_unit - value_split)
                            value_split += value

                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = value
                        else:
                            towrite_dict[valuation.id] += value
        if towrite_dict:
            for key, value in towrite_dict.items():
                line_obj.write(cr, uid, key, {'additional_landed_cost': value}, context=context)
        return True
