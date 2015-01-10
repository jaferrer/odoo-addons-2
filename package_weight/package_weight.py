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
from openerp import fields, models, api

class stock_package_with_weights(models.Model):
    _inherit = "stock.quant.package"
    weight = fields.Float("Gross Weight",compute="_compute_weight", help="Gross weight")
    weight_net = fields.Float("Net Weight",compute="_compute_weight", help="Net weight")

    @api.multi
    @api.depends('quant_ids.product_id.weight','quant_ids.qty','ul_id.weight')
    def _compute_weight(self):
        for rec in self:
            weight = 0
            weight_net = 0
            for line in rec.quant_ids:
                weight += line.product_id.weight * line.qty
                weight_net += line.product_id.weight_net * line.qty
            for line in rec.children_ids:
                 weight += line.weight
                 weight_net += line.weight_net
            ul_weight = rec.ul_id and rec.ul_id.weight or 0.0
            rec.weight = weight + ul_weight
            rec.weight_net = weight_net

