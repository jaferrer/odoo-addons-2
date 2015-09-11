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


class StockQuantPackageMove(models.TransientModel):
    _name = 'stock.quant.package.move'

    pack_move_items = fields.One2many(
        comodel_name='stock.quant.package.move_items', inverse_name='move_id',
        string='Packs')

    global_dest_loc = fields.Many2one(
        comodel_name='stock.location', string='Destination Location',
        required=True)

    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type')

    def default_get(self, cr, uid, fields, context=None):
        res = super(StockQuantPackageMove, self).default_get(
            cr, uid, fields, context=context)
        packages_ids = context.get('active_ids', [])
        if not packages_ids:
            return res
        packages_obj = self.pool['stock.quant.package']
        packages = packages_obj.browse(cr, uid, packages_ids, context=context)
        items = []
        for package in packages:
            if not package.parent_id and package.location_id:
                item = {
                    'package': package.id,
                    'source_loc': package.location_id.id,
                }
                items.append(item)
        res.update(pack_move_items=items)
        return res

    @api.one
    def do_detailed_transfer(self):
        quants = self.pack_move_items.filtered(lambda x: x.dest_loc != x.source_loc).mapped(lambda x: x.package.quant_ids)
        quants.move_to(self.global_dest_loc, self.picking_type_id)
        #quants2 = (self.pack_move_items.filtered(lambda x: x.dest_loc != x.source_loc)).mapped(lambda x: x.package.children_ids.quant_ids)
        #quants2.move_to(self.global_dest_loc, self.picking_type_id)
        return True

class StockQuantPackageMoveItems(models.TransientModel):
    _name = 'stock.quant.package.move_items'
    _description = 'Picking wizard items'

    move_id = fields.Many2one(
        comodel_name='stock.quant.package.move', string='Package move')
    package = fields.Many2one(
        comodel_name='stock.quant.package', string='Quant package',
        domain=[('parent_id', '=', False), ('location_id', '!=', False)])
    source_loc = fields.Many2one(
        comodel_name='stock.location', string='Source Location')
    dest_loc = fields.Many2one(
        comodel_name='stock.location', string='Destination Location')

    @api.one
    @api.onchange('package')
    def onchange_quant(self):
        self.source_loc = self.package.location_id