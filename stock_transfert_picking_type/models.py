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

from openerp import models, fields, api, exceptions, _


class StockTransfertPickingTypeTransferDetails(models.TransientModel):
    _inherit = 'stock.transfer_details'

    item_expedition_ids = fields.One2many('stock.transfer_details_items', 'transfer_id', 'Items',
                                          domain=[('product_id', '!=', False)])
    item_reception_ids = fields.One2many('stock.transfer_details_items', 'transfer_id', 'Items',
                                         domain=[('product_id', '!=', False)])
    picking_type_code = fields.Char(u"Picking Type Code", related="picking_id.picking_type_code", readonly=True)

    @api.model
    def default_get(self, fields_list):
        result = super(StockTransfertPickingTypeTransferDetails, self).default_get(fields_list)
        picking = self.env['stock.picking'].browse(self.env.context['active_id'])
        items = result.get('item_ids', []) + result.get('packop_ids', [])
        if picking.picking_type_code == 'incoming':
            for item in items:
                if item.get('packop_id'):
                    packop = self.env['stock.pack.operation'].browse([item['packop_id']])
                    item['purchase_line_id'] = packop.purchase_line_id and packop.purchase_line_id.id or False
        if picking.picking_type_code == 'outgoing':
            for item in items:
                if item.get('packop_id'):
                    packop = self.env['stock.pack.operation'].browse([item['packop_id']])
                    item['sale_line_id'] = packop.sale_line_id and packop.sale_line_id.id or False
        return result

class ReceptionByOrderTransferDetailsItems(models.TransientModel):
    _inherit = 'stock.transfer_details_items'

    purchase_line_id = fields.Many2one('purchase.order.line', string="Purchase order line")
    sale_line_id = fields.Many2one('sale.order.line', string="Sale order line")
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

    sale_line_id = fields.Many2one('sale.order.line', string="Sale order line")
    purchase_line_id = fields.Many2one('purchase.order.line', string="Purchase order line")
    picking_type_code = fields.Char(u"Picking Type Code", related="picking_id.picking_type_code", readonly=True)


class StockTransfertPickingTypeStokMove(models.Model):
    _inherit = 'stock.move'

    sale_line_id = fields.Many2one('sale.order.line', string="Sale order line")
