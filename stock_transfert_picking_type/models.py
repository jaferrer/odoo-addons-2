# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api


class StockTransfertPickingTypeTransferDetails(models.TransientModel):
    _inherit = 'stock.transfer_details'

    picking_type_code = fields.Char(string=u"Picking Type Code", related='picking_id.picking_type_code', readonly=True)
    picking_group_name = fields.Char(string="Procurement group name", related='picking_id.group_id.name', readonly=True)


class ReceptionByOrderTransferDetailsItems(models.TransientModel):
    _inherit = 'stock.transfer_details_items'

    group_name = fields.Char(string="Picking group name", related='transfer_id.picking_id.group_id.name', readonly=True)


class StockTransfertPickingTypeStockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.cr_uid_ids_context
    def do_enter_transfer_details(self, cr, uid, picking, context=None):
        pick = self.pool.get('stock.picking').browse(cr, uid, picking, context)
        if not context:
            context = {}
        context = dict(context)
        context['picking_type_code'] = pick.picking_type_code
        return super(StockTransfertPickingTypeStockPicking, self).do_enter_transfer_details(cr, uid, picking, context)

class StockTransfertPickingTypePackOp(models.Model):
    _inherit = 'stock.pack.operation'

    picking_type_code = fields.Char(u"Picking Type Code", related="picking_id.picking_type_code", readonly=True)
    group_name = fields.Char(string="Picking group name", related='picking_id.group_id.name', readonly=True)
