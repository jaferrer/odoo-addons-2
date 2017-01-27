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

from openerp import models, fields, api, exceptions, _


class ReceptionByOrderTransferDetails(models.TransientModel):
    _inherit = 'stock.transfer_details'

    @api.model
    def default_get(self, fields_list):
        result = super(ReceptionByOrderTransferDetails, self).default_get(fields_list)
        for item in result.get('item_ids', []) + result.get('packop_ids', []):
            if item.get('packop_id'):
                packop = self.env['stock.pack.operation'].browse([item['packop_id']])
                item['purchase_line_id'] = packop.purchase_line_id and packop.purchase_line_id.id or False
        return result

    @api.one
    def do_detailed_transfer(self):
        linked_purchase_orders = set([item.purchase_line_id.order_id for item in self.item_ids if
                                      item.purchase_line_id])
        if len(linked_purchase_orders) > 1:
            raise exceptions.except_orm(_("Error!"), _("Impossible to receive two different purchase orders at the "
                                                       "same time. Please check your packing operationd and retry."))
        if any([item.purchase_line_id and item.product_id != item.purchase_line_id.product_id for
                item in self.item_ids]):
            raise exceptions.except_orm(_("Error!"), _("Impossible to receive a product on a purchase order line "
                                                       "linked to another product. Please check your packing "
                                                       "operationd and retry."))
        # Create new pack operations if needed
        for item in self.item_ids:
            if not item.packop_id:
                new_packop = self.env['stock.pack.operation'].create({
                    'picking_id': self.picking_id and self.picking_id.id or False,
                    'product_id': item.product_id and item.product_id.id or False,
                    'product_uom_id': item.product_uom_id and item.product_uom_id.id or False,
                    'product_qty': item.quantity,
                    'package_id': item.package_id and item.package_id.id or False,
                    'lot_id': item.lot_id and item.lot_id.id or False,
                    'location_id': item.sourceloc_id and item.sourceloc_id.id or False,
                    'location_dest_id': item.destinationloc_id and item.destinationloc_id.id or False,
                    'result_package_id': item.result_package_id and item.result_package_id.id or False,
                    'date': item.date or fields.Datetime.now(),
                    'owner_id': item.owner_id and item.owner_id.id or False,
                })
                item.packop_id = new_packop
            item.packop_id.purchase_line_id = item.purchase_line_id
        return super(ReceptionByOrderTransferDetails, self).do_detailed_transfer()


class ReceptionByOrderTransferDetailsItems(models.TransientModel):
    _inherit = 'stock.transfer_details_items'

    purchase_line_id = fields.Many2one('purchase.order.line', string="Purchase order line")
    group_name = fields.Char(string="Picking group name", related='transfer_id.picking_id.group_id.name',
                             readonly=True)
