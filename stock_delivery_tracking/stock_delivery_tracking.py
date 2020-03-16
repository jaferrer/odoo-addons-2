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

    number_pickings = fields.Integer(u"Number of related Pickings", compute='_compute_number_pickings')
    number_quant_package = fields.Integer(u"Number of related Package", compute='_compute_number_quant_package')

    @api.multi
    def _compute_number_pickings(self):
        groupby = fields = ['transporter_id']
        res = self.env['stock.picking'].read_group([('transporter_id', 'in', self.ids)], fields, groupby)
        res = {it['transporter_id'][0]: it['transporter_id_count'] for it in res if it['transporter_id']}
        for rec in self:
            rec.number_pickings = res.get(rec.id, 0)

    @api.multi
    def _compute_number_quant_package(self):
        groupby = fields = ['transporter_id']
        res = self.env['stock.quant.package'].read_group([('transporter_id', 'in', self.ids)], fields, groupby)
        res = {it['transporter_id'][0]: it['transporter_id_count'] for it in res if it['transporter_id']}
        for rec in self:
            rec.number_quant_package = res.get(rec.id, 0)

    @api.multi
    def open_pickings(self):
        self.ensure_one()
        return {
            'name': _('Pickings related to transporter %s' % self.name),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'domain': [('transporter_id', '=', self.id)]
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
            'domain': [('transporter_id', '=', self.id)]
        }

class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    transporter_id = fields.Many2one('tracking.transporter', u"Transporteur")
    tracking_id = fields.Many2one('tracking.number', u"Tracking number")

    @api.onchange('tracking_id')
    def _onchange_tracking_id(self):
        self.transporter_id = self.tracking_id.transporter_id

class TrackingNumber(models.Model):
    _inherit = 'tracking.number'

    picking_id = fields.Many2one('stock.picking', u"Stock picking", readonly=True)
    group_id = fields.Many2one('procurement.group', u"Procurement Group")

    @api.multi
    def _compute_partner_id(self):
        super(TrackingNumber, self)._compute_partner_id()
        for rec in self:
            if rec.picking_id:
                rec.partner_id = rec.picking_id.partner_id


class DeliveryTrackingStockPicking(models.Model):
    _inherit = 'stock.picking'

    transporter_id = fields.Many2one('tracking.transporter', u"Transporter used",
                                     related='tracking_ids.transporter_id', store=True, readonly=True)
    last_status_update = fields.Datetime(u"Date of the last update")
    tracking_ids = fields.One2many('tracking.number', 'picking_id', u"Delivery Tracking")
