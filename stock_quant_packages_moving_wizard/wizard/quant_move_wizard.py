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

from openerp import models, fields, api, _, exceptions
from openerp.exceptions import ValidationError


class StockQuantMove(models.TransientModel):
    _name = 'stock.quant.move'

    pack_move_items = fields.One2many('stock.quant.move_items', 'move_id', string="Packages")
    global_dest_loc = fields.Many2one('stock.location', string='Destination Location', required=True)
    is_manual_op = fields.Boolean(string="Manual Operation")
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking type', required=True)

    def default_get(self, cr, uid, fields, context=None):
        res = super(StockQuantMove, self).default_get(
            cr, uid, fields, context=context)
        quants_ids = context.get('active_ids', [])
        if not quants_ids:
            return res
        quant_obj = self.pool['stock.quant']
        quants = quant_obj.browse(cr, uid, quants_ids, context=context)
        items = []
        for quant in quants:
            if not quant.package_id:
                item = {
                    'quant': quant.id,
                    'source_loc': quant.location_id.id,
                    'qty': quant.qty
                }
                items.append(item)
        res.update(pack_move_items=items)
        natural_dest_loc, natural_picking_type = quants.get_natural_loc_picking_type()
        global_dest_loc, picking_type = quants[0].location_id.get_default_loc_picking_type(quants[0].product_id)
        global_dest_loc = natural_dest_loc or global_dest_loc
        picking_type = natural_picking_type or global_dest_loc
        res.update(global_dest_loc=global_dest_loc and global_dest_loc.id or False)
        res.update(picking_type_id=picking_type and picking_type.id or False)
        return res

    @api.multi
    def do_transfer(self):
        self.ensure_one()
        quants = self.pack_move_items.mapped(lambda x: x.quant)
        move_items = {}
        for item in self.pack_move_items:
            move_items = item.quant.partial_move(move_items, item.quant.product_id, item.qty)
        new_picking = quants.with_context(mail_notrack=True). \
            move_to(self.global_dest_loc, self.picking_type_id, move_items, self.is_manual_op)
        return new_picking.open_picking_form(self.is_manual_op)


class StockQuantMoveItems(models.TransientModel):
    _name = 'stock.quant.move_items'
    _description = 'Picking wizard items'

    move_id = fields.Many2one('stock.quant.move', string='Quant move')
    quant = fields.Many2one('stock.quant', string='Quant', domain=[('package_id', '=', False)])
    source_loc = fields.Many2one('stock.location', string='Source Location', required=True)
    dest_loc = fields.Many2one('stock.location', string='Destination Location')
    qty = fields.Float(string='Quantity', required=True)

    @api.one
    @api.onchange('quant')
    def onchange_quant(self):
        self.source_loc = self.quant.location_id

    @api.one
    @api.constrains('qty')
    def _check_description(self):
        if self.qty > self.quant.qty:
            raise ValidationError(_("Fields qty must be lower than the initial quant quantity"))
