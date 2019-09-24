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

from openerp import models, api
from openerp.tools.float_utils import float_compare


class PurchaseProcurementStockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def action_done(self):
        result = super(PurchaseProcurementStockMove, self).action_done()
        reception_moves = self.search([('id', 'in', self.ids), ('purchase_line_id', '!=', False)])
        for reception_move in reception_moves:
            qty_to_switch_to_done = reception_move.product_uom_qty
            end_loop = False
            for pol_procurement in reception_move.purchase_line_id.procurement_ids:
                pol_procurement_qty_move_uom = self.env['product.uom']._compute_qty(pol_procurement.product_uom.id,
                                                                                    pol_procurement.product_qty,
                                                                                    reception_move.product_uom.id)
                if float_compare(qty_to_switch_to_done, 0,
                                 precision_rounding=reception_move.product_uom.rounding) != 0 and \
                        float_compare(pol_procurement_qty_move_uom, qty_to_switch_to_done,
                                      precision_rounding=reception_move.product_uom.rounding) > 0:
                    new_proc = pol_procurement.split(pol_procurement.product_qty - qty_to_switch_to_done, force_state='running')
                    end_loop = True
                pol_procurement.forced_to_done_by_reception = True
                pol_procurement.check()
                qty_to_switch_to_done -= pol_procurement.product_qty
                if end_loop:
                    break
        return result


class PurchaseProcurementStockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    @api.model
    def get_query_move_in(self):
        return """SELECT
      sm.id,
      sm.product_qty,
      min(COALESCE(po.date_planned, sm.date)) AS date,
      po.id
    FROM
      stock_move sm
      LEFT JOIN stock_location sl ON sm.location_dest_id = sl.id
      LEFT JOIN procurement_order po ON sm.procurement_id = po.id
    WHERE
      sm.product_id = %s
      AND sm.state NOT IN ('cancel', 'done', 'draft')
      AND sm.purchase_line_id IS NULL
      AND sl.parent_left >= %s
      AND sl.parent_left < %s"""