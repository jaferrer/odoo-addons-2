# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api, _
from openerp.exceptions import UserError


class ForceFillPackopsQty(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def get_picking_types_force_transfer_qty(self):
        self.ensure_one()
        return self.env['stock.picking.type']

    @api.multi
    def get_picking_zero_validation(self):
        self.ensure_one()
        return False

    @api.multi
    def do_new_transfer(self):
        for pick in self:
            to_delete = self.env['stock.pack.operation']
            if not pick.move_lines and not pick.pack_operation_ids:
                raise UserError(_('Please create some Initial Demand or Mark as Todo and create some Operations. '))
            # In draft or with no pack operations edited yet, ask if we can just do everything
            if pick.state == 'draft' or pick.get_picking_zero_validation():
                # If no lots when needed, raise error
                picking_type = pick.picking_type_id
                if picking_type.use_create_lots or picking_type.use_existing_lots:
                    for pack in pick.pack_operation_ids:
                        if pack.product_id and pack.product_id.tracking != 'none':
                            raise UserError(_('Some products require lots, so you need to specify those first!'))
                view = self.env.ref('stock.view_immediate_transfer')
                wiz_id = self.env['stock.immediate.transfer'].create({'pick_id': pick.id})
                return {
                    'name': _('Immediate Transfer?'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.immediate.transfer',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'res_id': wiz_id.id,
                    'context': self.env.context,
                }

            picking_types_force_transfer_qty = pick.get_picking_types_force_transfer_qty()
            # Check backorder should check for other barcodes
            if self.check_backorder(pick) and pick.picking_type_id not in picking_types_force_transfer_qty:
                view = self.env.ref('stock.view_backorder_confirmation')
                wiz_id = self.env['stock.backorder.confirmation'].create({'pick_id': pick.id})
                return {
                    'name': _('Create Backorder?'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.backorder.confirmation',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'res_id': wiz_id.id,
                    'context': self.env.context,
                }
            if pick.picking_type_id in picking_types_force_transfer_qty:
                for op in pick.pack_operation_ids:
                    if op.qty_done < op.product_qty:
                        raise UserError(_('All the products should be transfered'))

            for operation in pick.pack_operation_ids:
                if operation.qty_done < 0:
                    raise UserError(_('No negative quantities allowed'))
                if operation.qty_done > 0:
                    operation.product_qty = operation.qty_done
                else:
                    to_delete |= operation
            if to_delete:
                to_delete.unlink()
        self.do_transfer()
        return
