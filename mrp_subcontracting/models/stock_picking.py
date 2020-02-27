# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def action_done(self):
        res = super(StockPicking, self).action_done()
        for rec in self:
            if rec.picking_type_id == self.env.ref('stock.picking_type_out'):
                rec.move_lines.mapped('production_move_id').action_subcontracting_sended()
            elif rec.picking_type_id == self.env.ref('stock.picking_type_in'):
                for purchase_line in self.mapped('move_lines').mapped('purchase_line_id'):
                    production_sub = \
                        self.env['mrp.production'].search([('purchase_line_subcontract_id', '=', purchase_line.id)])
                    if purchase_line.qty_received == sum(production_sub.mapped('product_qty')):
                        production_sub.action_subcontracting_done()
        return res
