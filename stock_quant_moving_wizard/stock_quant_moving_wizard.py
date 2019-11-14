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

from odoo import api, models, fields, exceptions, _


class HamacStockQuantMovingWizard(models.TransientModel):
    _name = 'stock.quant.moving.wizard'

    location_id = fields.Many2one('stock.location', u"Origin location", required=True)
    location_dest_id = fields.Many2one('stock.location', u"Destination location", required=False)

    @api.multi
    def create_stock_operation(self):
        self.ensure_one()
        ctx = dict(self._context)
        ctx.update({
            'default_picking_type_id': self.env.ref('hamac_data.hamac_picking_type_manual').id,
            'default_location_id': self.location_id.id,
            'default_location_dest_id': self.location_dest_id.id,
            'default_move_lines': [(0, 0, {
                'name': quant.product_id.name,
                'product_id': quant.product_id.id,
                'product_uom_qty': quant.qty,
                'product_uom': quant.product_id.uom_id.id,
                'location_id': self.mapped('location_id')[0].id,
                'location_dest_id': self.location_dest_id.id,
                'picking_type_id': self.env.ref('hamac_data.hamac_picking_type_manual').id,
                'scrapped': False,
                'state': 'draft',
                'date_expected': fields.Datetime.now(),
            }) for quant in self.env['stock.quant'].browse(self._context['active_ids'])],
        })
        return {
            'name': _(u"Create a stock operation"),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'context': ctx,
        }


class HamacStockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.multi
    def create_stock_moving_wizard(self):
        if len(self.mapped('location_id')) != 1:
            raise exceptions.ValidationError(
                _(u"You cannot move stock from different locations!"))
        wiz = self.env['stock.quant.moving.wizard'].create({
            'location_id': self.mapped('location_id')[0].id,
        })
        return {
            'name': _(u"Create a stock operation"),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant.moving.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_id': wiz.id,
            'context': self._context,
        }
