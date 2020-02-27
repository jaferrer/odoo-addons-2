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

from odoo import models, fields, api, _

from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    picking_out_count = fields.Integer(compute='_compute_picking_out', string='Picking out count', default=0)
    picking_out_ids = fields.Many2many('stock.picking', compute='_compute_picking_out', string='Livraison', copy=False)

    @api.multi
    def _compute_picking_out(self):
        for rec in self:
            picking_out_ids = self.env['stock.picking'].search([
                ('origin', '=', rec.name),
                ('picking_type_id', '=', self.env.ref('stock.picking_type_out').id)
            ])
            rec.picking_out_ids = picking_out_ids
            rec.picking_out_count = len(picking_out_ids)

    @api.multi
    def button_confirm(self):
        super(PurchaseOrder, self).button_confirm()
        for rec in self:
            for line in rec.order_line:
                # On rajoute le production_move_id dans le bon de reception
                mrp_production = self.env['mrp.production'].search([('purchase_line_subcontract_id', '=', line.id)])

                # Si l'of est sous-traité
                stock_move = self.env['stock.move']
                for move in mrp_production.move_raw_ids:
                    stock_move |= move.copy({
                        'origin': rec.name,
                        'group_id': rec.group_id.id,
                        'raw_material_production_id': False,
                        'production_id': False,
                        'picking_type_id': self.env.ref('stock.picking_type_out').id,
                        'location_id': self.env.ref('stock.stock_location_stock').id,
                        'location_dest_id': self.env.ref('stock.stock_location_suppliers').id,
                        'production_move_id': mrp_production.id,
                    })
                if stock_move:
                    stock_move._action_confirm()

    @api.multi
    def button_cancel(self):
        res = super(PurchaseOrder, self).button_cancel()
        for rec in self:
            for picking_out in rec.picking_out_ids:
                if picking_out.state != 'done':
                    picking_out.action_cancel()
                else:
                    raise UserError(_('Unable to cancel purchase order %s as some receptions have already been done.')
                                    % rec.name)
            rec.mapped('order_line').mapped('production_move_id').action_subcontracting_cancel()
        return res

    @api.multi
    def action_view_picking_out(self):
        """ This function returns an action that display existing picking orders of given purchase order ids.
         When only one found, show the picking immediately.
        """
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]
        # override the context to get rid of the default filtering on operation type
        result['context'] = {}
        pick_ids = self.mapped('picking_out_ids')
        # choose the view_mode accordingly
        if not pick_ids or len(pick_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % (pick_ids.ids)
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = pick_ids.id
        return result
