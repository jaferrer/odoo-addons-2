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


class TrackingStatus(models.Model):
    _name = 'tracking.status'

    tracking_id = fields.Many2one('tracking.number', string="Linked tracking number")
    date = fields.Datetime(string="Status Date")
    status = fields.Char(string="Delivery Status")


class TrackingNumber(models.Model):
    _name = 'tracking.number'

    name = fields.Char(string="Tracking number", required=True)
    status_ids = fields.One2many('tracking.status', 'tracking_id', string="Status history")
    date = fields.Datetime(string="Date of the status", compute='_compute_date_and_status')
    status = fields.Char(string="Status", compute='_compute_date_and_status')
    order_id = fields.Many2one('purchase.order', string="Linked purchase order")

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
            'name': _('List of status corresponding to this tracking number'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'list',
            'res_model': 'tracking.status',
            'domain': [('tracking_id', '=', self.id)]
        }


class PurchaseDeliveryTrackingPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    transporter_id = fields.Many2one('tracking.transporter', string="Transporter used")
    last_status_update = fields.Datetime(string="Date of the last update")
    tracking_ids = fields.One2many('tracking.number', 'order_id', string="Delivery Tracking")

    # Function to overwrite for each transporter.
    @api.multi
    def update_delivery_status(self):
        for rec in self:
            rec.last_status_update = fields.Datetime.now()
            rec.status_date = False
            rec.delivery_status = False
