# -*- coding: utf8 -*-
#
#    Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def action_scrap(self, quantity, location_id, restrict_lot_id=False, restrict_partner_id=False):
        """Move the scrap/damaged product into scrap location.

        Overridden here to recreate a procurement if we are in a chained move."""
        res = super(StockMove, self).action_scrap(quantity, location_id, restrict_lot_id=restrict_lot_id,
                                                  restrict_partner_id=restrict_partner_id)
        for move in self:
            if move.state not in ['done', 'cancel'] and move.procure_method == 'make_to_order':
                proc_vals = self._prepare_procurement_from_move(move)
                proc_vals.update({
                    'product_qty': quantity,
                    'product_uos_qty': quantity * move.product_uos_qty / move.product_uom_qty,
                })
                new_proc = self.env['procurement.order'].create(proc_vals)
                # We run the procurement immediately because when we scrap
                # in real life we need to resupply immediately
                new_proc.run()

        return res
