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

from openerp import models, fields, api, _
from openerp.exceptions import ValidationError


class IncompleteProductionProductProduce(models.TransientModel):
    _inherit = 'mrp.product.produce'

    def _get_default_production_id(self):
        order=False
        c = self.env.context
        if c and c.get("active_id"):
            order = self.env['mrp.production'].browse(c.get("active_id"))
        return order

    def _get_return_location_id(self):
        order=False
        c = self.env.context
        if c and c.get("active_id"):
            order = self.env['mrp.production'].browse(c.get("active_id"))
        return order.warehouse_id.return_location_id

    def _get_default_src_location(self):
        order=False
        c = self.env.context
        if c and c.get("active_id"):
            order = self.env['mrp.production'].browse(c.get("active_id"))
        if order:
            if order.child_location_id:
                return order.child_location_id
            else:
                return order.location_src_id
        else:
            return False

    def _get_default_dest_location(self):
        order=False
        c = self.env.context
        if c and c.get("active_id"):
            order = self.env['mrp.production'].browse(c.get("active_id"))
        if order:
            if order.child_location_id:
                return order.child_location_id
            else:
                return order.location_dest_id
        else:
            return False

    def _get_default_product_id(self):
        order=False
        c = self.env.context
        if c and c.get("active_id"):
            order = self.env['mrp.production'].browse(c.get("active_id"))
        if order:
            return order.product_id
        return order

    def _get_default_availability(self):
        order=False
        c = self.env.context
        if c and c.get("active_id"):
            order = self.env['mrp.production'].browse(c.get("active_id"))
        if order:
            for move in order.move_lines:
                if move.state != 'assigned':
                    return False
        return True

    production_id = fields.Many2one('mrp.production', string="Related Manufacturing Order",
                                    default=_get_default_production_id, readonly=True)
    create_child = fields.Boolean(string="Create a child manufacturing order", default=True)
    return_raw_materials = fields.Boolean(string="Return raw materials", default=True,
                                          help="Return not consumed raw materials and "
                                               "then create the child manufacturing order")
    return_location_id = fields.Many2one('stock.location', string="Return location",
                                         default=_get_return_location_id)
    child_production_product_id = fields.Many2one('product.product', default=_get_default_product_id,
                                                  string='Product of the child Manufacturing Order')
    child_src_loc_id = fields.Many2one('stock.location', string="Child source location",
            default=_get_default_src_location,
            help="If this field is empty, the child of this Manufacturing Order will have the same source location as "
                 "his parent. If it is filled, the child will have this location as source location.")
    child_dest_loc_id = fields.Many2one('stock.location', string="Child destination location",
                                        default=_get_default_dest_location, help="If this field is empty, the child of"
            " this Manufacturing Order will have the same destination location as his parent. If it is filled, the "
            "child will have this location as destination location.")
    production_all_available = fields.Boolean(string='True if the raw material of the related Manufacturing Order is '
                                              'entirely available', default=_get_default_availability, readonly=True)

    @api.constrains('create_child', 'child_production_product_id')
    def set_child_product_constrains(self):
        if self.create_child and not self.child_production_product_id:
            raise ValidationError(_("If you require a child order, you must specify a product for it."))
