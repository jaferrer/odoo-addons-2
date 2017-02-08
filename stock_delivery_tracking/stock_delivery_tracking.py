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

import base64

from openerp import models, fields, api, _


class TrackingTransporter(models.Model):
    _inherit = 'tracking.transporter'

    picking_ids = fields.One2many('stock.picking', 'transporter_id', groups='stock.group_stock_user',
                                  string="List of related pickings")
    number_pickings = fields.Integer(string="Number of related pickings", compute='_compute_number_pickings',
                                     groups='stock.group_stock_user', store=True)

    @api.depends('picking_ids')
    def _compute_number_pickings(self):
        for rec in self:
            rec.number_pickings = len(rec.picking_ids)

    @api.multi
    def open_pickings(self):
        self.ensure_one()
        return {
            'name': _('Pickings related to transporter %s' % self.name),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'domain': [('id', 'in', self.picking_ids.ids)]
        }

    @api.multi
    def open_packages(self):
        self.ensure_one()
        return {
            'name': _('Packages related to transporter %s' % self.name),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.quant.package',
            'domain': [('id', 'in', self.package_ids.ids)]
        }


class TrackingNumber(models.Model):
    _inherit = 'tracking.number'

    picking_id = fields.Many2one('stock.picking', string="Stock picking",
                                 groups='stock.group_stock_user')
    group_id = fields.Many2one('procurement.group', string="Procurement Group")

    @api.multi
    def _compute_partner_id(self):
        result = super(TrackingNumber, self)._compute_partner_id()
        for rec in self:
            if rec.picking_id:
                rec.partner_id = rec.picking_id.partner_id
        return result


class DeliveryTrackingStockPicking(models.Model):
    _inherit = 'stock.picking'

    transporter_id = fields.Many2one('tracking.transporter', string="Transporter used",
                                     related='tracking_ids.transporter_id', store=True, readonly=True)
    last_status_update = fields.Datetime(string="Date of the last update")
    tracking_ids = fields.One2many('tracking.number', 'picking_id', string="Delivery Tracking",
                                   groups='stock.group_stock_user')
