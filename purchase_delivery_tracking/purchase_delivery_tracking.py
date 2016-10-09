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


class TrackingTransporter(models.Model):
    _name = 'tracking.transporter'

    name = fields.Char(string="Name")
    image = fields.Binary(string="Image")
    number_ids = fields.One2many('tracking.number', 'transporter_id', domain=[('order_id', '!=', False)],
                                 string="List of related tracking numbers")
    order_ids = fields.One2many('purchase.order', 'transporter_id', groups='purchase.group_purchase_user',
                                string="List of related purchase orders")
    number_trackings = fields.Integer(string="Number of related tracking numbers", compute='_compute_number_trackings',
                                      store=True)
    number_orders = fields.Integer(string="Number of related purchase orders", compute='_compute_number_orders',
                                   groups='purchase.group_purchase_user', store=True)
    logo = fields.Char(compute='_compute_logo', string="Logo")

    @api.depends('number_ids')
    def _compute_number_trackings(self):
        for rec in self:
            rec.number_trackings = len(rec.number_ids)

    @api.depends('order_ids')
    def _compute_number_orders(self):
        for rec in self:
            rec.number_orders = len(rec.order_ids)

    # Function to overwrite for each transporter.
    @api.multi
    def _compute_logo(self):
        for rec in self:
            rec.logo = False

    @api.multi
    def open_transporter_numbers(self):
        self.ensure_one()
        return {
            'name': _('Tracking numbers related to transporter %s' % self.name),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'tracking.number',
            'domain': [('transporter_id', '=', self.id)]
        }

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


class TrackingStatus(models.Model):
    _name = 'tracking.status'

    tracking_id = fields.Many2one('tracking.number', string="Linked tracking number")
    date = fields.Datetime(string="Status Date")
    status = fields.Char(string="Delivery Status")


class TrackingNumber(models.Model):
    _name = 'tracking.number'

    name = fields.Char(string="Tracking number", required=True)
    status_ids = fields.One2many('tracking.status', 'tracking_id', string="Status history")
    date = fields.Datetime(string="Date of the last status", compute='_compute_date_and_status')
    status = fields.Char(string="Last status", compute='_compute_date_and_status')
    order_id = fields.Many2one('purchase.order', string="Linked purchase order",
                               groups='purchase.group_purchase_user')
    transporter_id = fields.Many2one('tracking.transporter', string="Transporter")
    partner_id = fields.Many2one('res.partner', string="Supplier", related='order_id.partner_id')
    last_status_update = fields.Datetime(string="Date of the last update")
    logo = fields.Char(string="Logo", related='transporter_id.logo')
    image = fields.Binary(string="Image", related='transporter_id.image')

    @api.multi
    def _compute_date_and_status(self):
        for rec in self:
            max_date = False
            status = False
            if rec.status_ids:
                max_date = max([status.date for status in rec.status_ids])
                status = rec.status_ids.filtered(lambda x: x.date == max_date)[0].status
            rec.date = max_date
            rec.status = status

    @api.multi
    def open_status_ids(self):
        self.ensure_one()
        return {
            'name': _('List of status corresponding to tracking number %s' % self.name),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'tracking.status',
            'domain': [('tracking_id', '=', self.id)]
        }

    # Function to overwrite for each transporter.
    @api.multi
    def update_delivery_status(self):
        for rec in self:
            rec.last_status_update = fields.Datetime.now()


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
