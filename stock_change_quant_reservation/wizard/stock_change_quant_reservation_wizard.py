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

from openerp import models, fields, api, exceptions, _


class StockChangeQuantPicking(models.TransientModel):
    _name = 'stock.quant.picking'

    @api.model
    def default_get(self, fields_list):
        quants = self.env['stock.quant'].browse(self.env.context['active_ids'])
        products = quants.mapped('product_id')
        if len(products) != 1:
            raise exceptions.except_orm(_("Error!"), _("Impossible to reserve quants of different products."))
        return {}

    partner_id = fields.Many2one('res.partner', string='Partner')
    picking_id = fields.Many2one('stock.picking', string='Picking', context={'reserving_quant': True})
    move_id = fields.Many2one('stock.move', string='Stock move', required=True, context={'reserving_quant': True})

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.ensure_one()
        self.picking_id = False
        groups = self.env['procurement.group'].search([('partner_id', '=', self.partner_id.id)])
        return self.partner_id and {'domain': {'picking_id': [('group_id', 'in', groups.ids)]}} or {}

    @api.onchange('picking_id')
    def onchange_picking_id(self):
        self.ensure_one()
        self.move_id = False
        quant = self.env['stock.quant'].browse(self.env.context['active_ids'][0])
        return self.picking_id and {'domain': {'move_id': [('group_id', '=', self.picking_id.group_id.id),
                                                           ('product_id', '=', quant.product_id.id),
                                                           ('state', 'in', ['confirmed', 'waiting'])]}} or {}

    @api.multi
    def do_apply(self):
        self.ensure_one()
        quants_ids = self.env.context.get('active_ids', [])
        quants = self.env['stock.quant'].browse(quants_ids)
        for quant in quants:
            self.env['stock.quant'].quants_unreserve(self.move_id)
            self.move_id.action_confirm()
            quant.quants_reserve([(quant, self.move_id.product_uom_qty)], self.move_id)
            break
        if self.picking_id.pack_operation_ids:
            self.move_id.picking_id.do_prepare_partial()
        return {
            'name': 'Stock Operation',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': self.move_id.picking_id.id
        }
