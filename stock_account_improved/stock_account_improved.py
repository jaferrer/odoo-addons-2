# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class StockAccountImprovedStockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def default_get(self, fields_list):
        result = super(StockAccountImprovedStockMove, self).default_get(fields_list)
        print 'default', result
        print 'ctx', self.env.context
        picking_id = result.get('default_picking_id') or self.env.context.get('default_picking_id')
        if picking_id:
            picking = self.env['stock.picking'].browse(picking_id)
            if picking.invoice_state:
                result['invoice_state'] = picking.invoice_state
        print 'result', result
        return result
