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

_PROVIDER = [('other', "Other")]


class DeliveryCarrierProvider(models.Model):
    _name = 'delivery.carrier.provider'
    _description = 'Delivery Carrier Provider'

    name = fields.Char("Delivery Carrier Provider")
    active = fields.Boolean(default=True)
    debug_logging = fields.Boolean("Debug mode", default=False)
    prod_environment = fields.Boolean("Test mode", default=False)
    color = fields.Integer("Color", compute='_compute_color')
    image = fields.Binary("Image")
    company_id = fields.Many2one('res.company', string="Company", required=True, groups='base.group_multi_company',
                                 default=lambda self: self.env.user.company_id)
    get_tracking_link_ok = fields.Boolean("Can get tracking link", compute='_compute_integration')
    cancel_shipment_ok = fields.Boolean("Can cancel tracking", compute='_compute_integration')
    rate_shipment_ok = fields.Boolean("Can rate shipment", compute='_compute_integration')
    send_shipping_ok = fields.Boolean("Can send shipping", compute='_compute_integration')
    get_default_custom_package_code_ok = fields.Boolean("Can get default custom package code",
                                                        compute='_compute_integration')
    carrier = fields.Selection(_PROVIDER, "Provider", required=True, default='other')
    delivery_carrier_ids = fields.One2many('delivery.carrier', 'provider_id', string="Delivery carriers")

    @api.multi
    def write(self, vals):
        res = super(DeliveryCarrierProvider, self).write(vals)
        to_propagate = {}
        if not vals.get('active', True):
            to_propagate['active'] = False
        if 'debug_logging' in vals:
            to_propagate['debug_logging'] = vals['debug_logging']
        if 'prod_environment' in vals:
            to_propagate['prod_environment'] = vals['prod_environment']
        if to_propagate:
            print(to_propagate)
            self.mapped('delivery_carrier_ids').write(to_propagate)
        return res

    @api.multi
    def _compute_color(self):
        for rec in self:
            rec.color = 10
            if rec.prod_environment:
                rec.color = 3
            if not rec.active:
                rec.color = 7

    @api.multi
    def _compute_integration(self):
        carrier = self.env['delivery.carrier']
        for rec in self:
            code = rec.carrier
            rec.rate_shipment_ok = hasattr(carrier, '%s_rate_shipment' % code)
            rec.send_shipping_ok = hasattr(carrier, '%s_send_shipping' % code)
            rec.get_tracking_link_ok = hasattr(carrier, '%s_get_tracking_link' % code)
            rec.cancel_shipment_ok = hasattr(carrier, '%s_cancel_shipment' % code)
            rec.get_default_custom_package_code_ok = hasattr(carrier, '%s_get_default_custom_package_code' % code)

    @api.model
    def _get_by_code(self, code):
        return self.search([('carrier', '=', code)])

    @api.multi
    def action_view_delivery_carrier(self):
        self.ensure_one()
        action = self.env.ref('delivery.action_delivery_carrier_form').read()[0]
        action['domain'] = [('provider_id', '=', self.id)]
        return action

    @api.multi
    def action_view_logging(self):
        self.ensure_one()
        action = self.env.ref('base.ir_logging_all_act').read()[0]
        action['domain'] = [
            ('name', '=', 'delivery.carrier'),
            ('path', '=', self.carrier)
        ]
        return action

    @api.multi
    def toggle_prod_environment(self):
        for rec in self:
            rec.prod_environment = not rec.prod_environment

    @api.multi
    def toggle_debug(self):
        for rec in self:
            rec.debug_logging = not rec.debug_logging
