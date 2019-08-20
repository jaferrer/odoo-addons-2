# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def split(self, move, qty, restrict_lot_id=False, restrict_partner_id=False):
        split_move_id = super(StockMove, self).split(move, qty, restrict_lot_id, restrict_partner_id)
        self.split_proc_for_move(new_move=self.search([('id', '=', split_move_id)]), current_move=move)
        return split_move_id

    def split_proc_for_move(self, new_move, current_move=False):
        proc = new_move.procurement_id
        if proc:
            new_proc = proc.split(new_move.product_uom_qty,
                                  force_move_dest_id=new_move.move_dest_id.id,
                                  force_state='running')
            new_move.procurement_id = new_proc
            new_proc.check()
            proc.check()


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    split_from_id = fields.Many2one('procurement.order', string=u"Split From", readonly=True,
                                    ondelete='set null', index=True)

    @api.multi
    def split(self, qty, force_move_dest_id=False, force_state=False):
        self.ensure_one()
        new_procurement = self.copy({
                'state': force_state or 'confirmed',
                'product_qty': qty,
                'product_uos_qty': qty,
                'move_dest_id': force_move_dest_id,
                'split_from_id': self.id
            })
        self.write({
            'product_qty': self.product_qty - qty,
            'product_uos_qty': self.product_uos_qty - qty,
        })
        return new_procurement
