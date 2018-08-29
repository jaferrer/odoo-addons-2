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

    item_expedition_ids = fields.One2many('stock.transfer_details_items', 'transfer_id', 'Items',
                                          domain=[('product_id', '!=', False)])
    item_reception_ids = fields.One2many('stock.transfer_details_items', 'transfer_id', 'Items',
                                         domain=[('product_id', '!=', False)])
    picking_type_code = fields.Char(string=u"Picking Type Code", related='picking_id.picking_type_code', readonly=True)
    picking_group_name = fields.Char(string="Procurement group name", related='picking_id.group_id.name', readonly=True)


class ReceptionByOrderTransferDetailsItems(models.TransientModel):
    _inherit = 'stock.transfer_details_items'

    group_name = fields.Char(string="Picking group name", related='transfer_id.picking_id.group_id.name',
                             readonly=True)


class StockTransfertPickingTypeProcOrder(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _run_move_create(self, procurement):
        res = super(StockTransfertPickingTypeProcOrder, self)._run_move_create(procurement)
        res.update({'sale_line_id': procurement.sale_line_id and procurement.sale_line_id.id or False})
        return res


class StockTransfertPickingTypeStockPicking(models.Model):
    _inherit = 'stock.picking'

    pack_operation_expedition_ids = fields.One2many('stock.pack.operation', 'picking_id',
                                                    states={'done': [('readonly', True)],
                                                            'cancel': [('readonly', True)]},
                                                    string=u'Related Packing Operations')
    pack_operation_reception_ids = fields.One2many('stock.pack.operation', 'picking_id',
                                                   states={'done': [('readonly', True)],
                                                           'cancel': [('readonly', True)]},
                                                   string=u'Related Packing Operations')

class StockTransfertPickingTypePackOp(models.Model):
    _inherit = 'stock.pack.operation'

    picking_type_code = fields.Char(u"Picking Type Code", related="picking_id.picking_type_code", readonly=True)
    group_name = fields.Char(string="Picking group name", related='picking_id.group_id.name', readonly=True)
