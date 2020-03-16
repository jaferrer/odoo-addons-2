# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import models, api


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    @api.multi
    def recursive_explode(self, product, quantity, picking_type=False):
        self.ensure_one()
        boms, lines = self.explode(product, quantity, picking_type)
        dict_boms = dict(boms)
        res = {}
        for bom_line, res_dict in lines:
            # if bom_line.product_id not in res:
            if bom_line.child_bom_id:
                bom_exploded, result = bom_line.child_bom_id.recursive_explode(
                    bom_line.product_id, res_dict['qty'], picking_type
                )
                # Merge bom_exploded in bom
                for bom_exp, bom_exp_dict in bom_exploded:
                    dict_boms.setdefault(bom_exp, dict(bom_exp_dict, qty=0))
                    dict_boms[bom_exp]['qty'] += bom_exp_dict['qty']
                # Merge result in res
                for result_product, result_qty in result:
                    res.setdefault(result_product, 0)
                    res[result_product] += result_qty
            else:
                res.setdefault(bom_line.product_id, 0)
                res[bom_line.product_id] += res_dict.get('qty', 0)
        return dict_boms.items(), res.items()
