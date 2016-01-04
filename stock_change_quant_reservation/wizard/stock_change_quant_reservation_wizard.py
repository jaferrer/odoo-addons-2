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

from openerp import models, fields, api


class StockChangeQuantPicking(models.TransientModel):
    _name = 'stock.quant.picking'

    @api.model
    def _picking_list_get(self):
        quants_ids = self.env.context.get('active_ids', [])
        if not quants_ids:
            return []
        quants = self.env['stock.quant'].browse(quants_ids)
        items = []
        for quant in quants:
            if not quant.package_id:
                compare = items
                moves = self.env['stock.move'].search(['&', ('product_id', '=', quant.product_id.id),
                                                       ('state', 'not in', ['done', 'cancel'])])
                sublist = []
                for move in moves:
                    sublist.append(move.picking_id.id)
                if compare:
                    items = set(compare).intersection(set(sublist))
                else:
                    items = sublist

        return [('id', 'in', list(items))]

    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Picking', domain=_picking_list_get, required=True)

    @api.multi
    def do_apply(self):
        self.ensure_one()
        moves = self.picking_id.move_lines
        quants_ids = self.env.context.get('active_ids', [])
        quants = self.env['stock.quant'].browse(quants_ids)
        for quant in quants:
            for move in moves:
                if (move.product_id.id == quant.product_id.id):
                    self.env['stock.quant'].quants_unreserve(move)
                    move.action_confirm()
                    quant.quants_reserve([(quant, move.product_uom_qty)], move)
                    break

        self.picking_id.do_prepare_partial()
        return {
            'name': 'Stock Operation',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id
        }
