# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from odoo import fields, models, api

_PROVIDER = [('chronopost', "Chronopost")]


class DeliveryCarrierProvider(models.Model):
    _name = 'delivery.carrier.provider'
    _description = 'Delivery Carrier Provider'

    name = fields.Char("Delivery carrier provider")
    active = fields.Boolean(default=True)
    debug_mode = fields.Boolean("Debug mode")
    test_mode = fields.Boolean("Test mode")
    color = fields.Integer("Color", compute='_compute_color')
    image = fields.Binary("Image", compute='_compute_image')
    company_id = fields.Many2one('res.company', string="Company", required=True, groups='base.group_multi_company',
                                 default=lambda self: self.env.user.company_id)
    get_tracking_link_ok = fields.Boolean("Can get tracking link", compute='_compute_integration')
    cancel_shipment_ok = fields.Boolean("Can cancel tracking", compute='_compute_integration')
    rate_shipment_ok = fields.Boolean("Can rate shipment", compute='_compute_integration')
    send_shipping_ok = fields.Boolean("Can send shipping", compute='_compute_integration')
    get_default_custom_package_code_ok = fields.Boolean("Can get default custom package code",
                                                        compute='_compute_integration')
    carrier = fields.Selection(_PROVIDER, "Provider", required=True)
    delivery_carrier_ids = fields.Many2many('delivery.carrier', string="Delivery carriers",
                                            context={'active_test': False})

    @api.multi
    def _compute_image(self):
        for rec in self:
            if hasattr(self.env['delivery.carrier'], '%s_compute_image' % rec.carrier):
                rec.image = getattr(self, '%s_compute_image' % rec.carrier)

    @api.multi
    def _compute_color(self):
        for rec in self:
            rec.color = 0
            if rec.test_mode:
                rec.color = 3
            if not rec.active:
                rec.color = 7

    @api.multi
    def _compute_integration(self):
        for rec in self:
            rec.rate_shipment_ok = hasattr(self.env['delivery.carrier'], '%s_rate_shipment' % rec.carrier)
            rec.send_shipping_ok = hasattr(self.env['delivery.carrier'], '%s_send_shipping' % rec.carrier)
            rec.get_tracking_link_ok = hasattr(self.env['delivery.carrier'], '%s_get_tracking_link' % rec.carrier)
            rec.cancel_shipment_ok = hasattr(self.env['delivery.carrier'], '%s_cancel_shipment' % rec.carrier)
            rec.get_default_custom_package_code_ok = hasattr(self.env['delivery.carrier'],
                                                             '%s_get_default_custom_package_code' % rec.carrier)

    @api.model
    def _get_by_code(self, code):
        return self.search([('carrier', '=', code)])

    def action_view_delivery_carrier(self):
        self.ensure_one()
        action = self.env.ref('delivery.action_delivery_carrier_form').read()[0]
        action['domain'] = [('carrier_id', '=', self.id)]
        return action

    def action_view_logging(self):
        self.ensure_one()
        action = self.env.ref('base.ir_logging_all_act').read()[0]
        action['domain'] = [
            ('name', '=', 'delivery.carrier'),
            ('path', '=', self.carrier)
        ]
        return action

    @api.multi
    def toggle_test_mode(self):
        for rec in self:
            rec.test_mode = not rec.test_mode
            for delivery_carrier_id in rec.delivery_carrier_ids:
                delivery_carrier_id.prod_environment = rec.test_mode

    def toggle_debug_mode(self):
        for rec in self:
            rec.debug_mode = not rec.debug_mode
            for delivery_carrier_id in rec.delivery_carrier_ids:
                delivery_carrier_id.debug_logging = rec.debug_mode

    def toggle_active(self):
        for rec in self:
            rec.active = not rec.active
            for delivery_carrier_id in rec.delivery_carrier_ids:
                delivery_carrier_id.active = rec.active
