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

from openerp import models, fields, api

class TrackingTransporter(models.Model):
    _inherit = 'tracking.transporter'

    number_ids = fields.One2many('tracking.number', 'transporter_id', domain=[('order_id', '!=', False)])
    order_ids = fields.One2many('purchase.order', 'transporter_id', groups='purchase.group_purchase_user',
                                string="List of related purchase orders")
    number_orders = fields.Integer(string="Number of related purchase orders", compute='_compute_number_orders',
                                   groups='purchase.group_purchase_user', store=True)

    @api.depends('order_ids')
    def _compute_number_orders(self):
        for rec in self:
            rec.number_orders = len(rec.order_ids)

    @api.multi
    def open_purchase_orders(self):
        self.ensure_one()
        return {
            'name': _('Purchase orders related to transporter %s' % self.name),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'domain': [('id', 'in', self.order_ids.ids)]
        }


class TrackingNumber(models.Model):
    _inherit = 'tracking.number'

    order_id = fields.Many2one('purchase.order', string="Linked purchase order",
                               groups='purchase.group_purchase_user')

    @api.multi
    def _compute_partner_id(self):
        result = super(TrackingNumber, self)._compute_partner_id()
        for rec in self:
            if rec.order_id:
                rec.partner_id = rec.order_id.partner_id
        return result


class PurchaseDeliveryTrackingPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    transporter_id = fields.Many2one('tracking.transporter', string="Transporter used",
                                     related='tracking_ids.transporter_id', store=True, readonly=True)
    last_status_update = fields.Datetime(string="Date of the last update")
    tracking_ids = fields.One2many('tracking.number', 'order_id', string="Delivery Tracking")

    @api.multi
    def update_delivery_status(self):
        for rec in self:
            if rec.state not in ['draft', 'cancel', 'done']:
                rec.last_status_update = fields.Datetime.now()
                rec.tracking_ids.update_delivery_status()
