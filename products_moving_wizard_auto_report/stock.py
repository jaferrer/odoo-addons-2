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

from openerp import models, api


class AutoReportStockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.multi
    def move_to(self, dest_location, picking_type, move_items=False, is_manual_op=False, filling_method=False):
        result = super(AutoReportStockQuant, self).move_to(dest_location, picking_type, move_items=move_items,
                                                           is_manual_op=is_manual_op, filling_method=filling_method)
        if not is_manual_op and result and result[0].picking_id.picking_type_id.report_id:
            return self.env['report'].with_context(active_ids=[result[0].picking_id.id]).get_action(
                    result[0].picking_id, result[0].picking_id.picking_type_id.report_id.report_name)
        return result
