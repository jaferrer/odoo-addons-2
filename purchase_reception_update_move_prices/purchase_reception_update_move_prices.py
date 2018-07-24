# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class UpdateMovePricesStockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def write(self, vals):
        if vals.get('state') == 'done':
            for rec in self:
                if rec.purchase_line_id:
                    price_unit = rec.purchase_line_id.get_move_unit_price_from_line()
                    rec.price_unit = price_unit
                    rec.quant_ids.sudo().write({'cost': price_unit})
        return super(UpdateMovePricesStockMove, self).write(vals)
