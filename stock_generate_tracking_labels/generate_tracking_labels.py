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

import os
import tempfile

from openerp import models, fields, api

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

PATH_BOT = tempfile.gettempdir() + os.sep + 'merger_bot'
PATH_TMP = PATH_BOT + os.sep + 'tmp'
if not os.path.exists(PATH_TMP):
    os.makedirs(PATH_TMP)


class DeliveryTrackingStockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    use_tracking_labels = fields.Boolean(u"Use tracking labels")


class DeliveryTrackingStockPicking(models.Model):
    _inherit = 'stock.picking'

    use_tracking_labels = fields.Boolean(u"Use tracking labels", related='picking_type_id.use_tracking_labels')
    tracking_defined = fields.Boolean(compute='_compute_tracking_defined')
    binary_label = fields.Binary(string="Label (binary)", attachment=True)
    data_fname = fields.Char(string="Label name")

    @api.multi
    def _compute_tracking_defined(self):
        for rec in self:
            rec.tracking_defined = bool(rec.tracking_ids)

    @api.multi
    def generate_tracking_labels(self):
        self.ensure_one()
        data = self._get_tracking_labels_wizard_data()
        return self.env['generate.tracking.labels.wizard'].create_and_get_action(data)

    @api.multi
    def _get_tracking_labels_wizard_data(self):
        self.ensure_one()
        data = {}
        warehouse_id = self.location_id and self.location_id.get_warehouse(self.location_id) or False
        warehouse = warehouse_id and self.env['stock.warehouse'].browse(warehouse_id) or False
        transporter, type_produit_id = self.get_produit(self.owner_id, self.move_lines[0].transporter_code)
        data['save_tracking_number'] = True
        data['picking_id'] = self.id
        data['transporter_id'] = transporter.id
        data['type_produit_id'] = self.type_produit_id.id
        data['produit_expedition_id'] = type_produit_id.id
        data['sender_parcel_ref'] = self.group_id.order_ref

        data['partner_orig_id'] = warehouse and warehouse.partner_id.id or False
        data['partner_id'] = self.partner_id and self.partner_id.id or False
        data['direction'] = self.picking_type_code == 'incoming' and 'from_customer' or 'to_customer'
        packages = self.pack_operation_product_ids.mapped('result_package_id')
        if packages:
            data['package_ids'] = [(6, 0, packages.ids)]
            data['weight'] = sum([pack.delivery_weight for pack in packages])
        return data

    @api.multi
    def update_delivery_status(self):
        for rec in self:
            rec.last_status_update = fields.Datetime.now()
            rec.tracking_ids.update_delivery_status()

    @api.multi
    def do_new_transfer(self):
        result = super(DeliveryTrackingStockPicking, self).do_new_transfer()
        for rec in self:
            for packop in rec.pack_operation_ids:
                computed_weight = packop.result_package_id.weight
                if computed_weight and not packop.result_package_id.delivery_weight:
                    packop.result_package_id.delivery_weight = computed_weight
        return result


class TrackingLabelStockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    delivery_weight = fields.Float(string=u"Package Weight (editable)")