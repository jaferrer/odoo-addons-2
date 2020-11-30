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

from odoo import fields, models, api, _


class StockQuickMoveWizard(models.TransientModel):
    _name = 'stock.quick.move.wizard'

    location_src_id = fields.Many2one('stock.location', string=u"Source Location", required=True)
    location_dest_id = fields.Many2one('stock.location', string=u"Destination Location", required=True)
    picking_type_id = fields.Many2one('stock.picking.type', string=u"Picking Type", required=True)
    product_id = fields.Many2one('product.product', string=u"Product", required=True)
    product_uom_id = fields.Many2one('product.uom', string=u"Unit Of Measure", related='product_id.uom_id',
                                     readonly=True)
    product_qty = fields.Float(u"Quantity", required=True)
    available_qty = fields.Float(u"Available Quantity", compute='_compute_available_qty')
    lot_id = fields.Many2one('stock.production.lot', string=u"Lot / Serial")
    validate_picking = fields.Boolean(u"Validate picking", default=True)
    tracking = fields.Selection(related='product_id.tracking')

    @api.multi
    @api.depends('product_id', 'lot_id', 'location_src_id')
    def _compute_available_qty(self):
        for rec in self:
            groups = self.env['stock.quant'].read_group(
                [('location_id', 'child_of', rec.location_src_id.id),
                 ('product_id', '=', rec.product_id.id),
                 ('lot_id', '=', rec.lot_id.id or False)],
                ['qty', 'product_id'], ['product_id'])
            rec.available_qty = groups and groups[0]['qty'] or 0

    @api.onchange('location_src_id')
    def onchange_location_src_id(self):
        self.product_id = False
        self.product_qty = 0
        self.lot_id = 0
        products = self.env['stock.quant'].read_group([('location_id', 'child_of', self.location_src_id.id)],
                                                      ['product_id'], ['product_id'])
        product_ids = [p['product_id'][0] for p in products if p['product_id']]
        return {'domain': {
            'product_id': [('id', 'in', product_ids)]
        }}

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.product_qty = 0
        self.lot_id = 0
        lots = self.env['stock.quant'].read_group(
            [('location_id', 'child_of', self.location_src_id.id), ('product_id', '=', self.product_id.id)],
            ['lot_id'], ['lot_id'])
        lot_ids = [l['lot_id'][0] for l in lots if l['lot_id']]
        return {'domain': {
            'lot_id': [('id', 'in', lot_ids)]
        }}

    @api.multi
    def apply(self):
        self.ensure_one()
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.location_src_id.id,
            'location_dest_id': self.location_dest_id.id,
            'move_lines': [(0, 0, {
                'name': self.product_id.display_name,
                'product_id': self.product_id.id,
                'product_uom': self.product_uom_id.id,
                'product_uom_qty': self.product_qty,
                'restrict_lot_id': self.lot_id.id,
                'picking_type_id': self.picking_type_id.id,
                'location_id': self.location_src_id.id,
                'location_dest_id': self.location_dest_id.id,
                'date_expected': fields.Datetime.now(),
            })]
        })
        picking.action_confirm()
        picking.action_assign()
        picking.do_prepare_partial()
        if self.validate_picking:
            picking.do_transfer()
        return {
            'name': _(u"New Picking"),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': picking.id,
            'context': self.env.context,
        }
