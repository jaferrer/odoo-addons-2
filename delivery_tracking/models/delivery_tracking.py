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

import base64

from odoo import fields, models, api, _ as _t
from .delivery_carrier_provider import _PROVIDER


class DeliveryCarrierTrackingNumber(models.Model):
    _name = 'delivery.carrier.tracking.number'
    _description = 'Tracking number'

    name = fields.Char("Tracking number")
    picking_id = fields.Many2one('stock.picking', "Picking", required=True)
    carrier_id = fields.Many2one('delivery.carrier', "Carrier")
    provider_id = fields.Many2one('delivery.carrier.provider', "Provider", related='carrier_id.provider_id', store=True)
    state = fields.Selection([('draft', "Draft"), ('send', "Send"), ('cancel', "Cancel")])
    binary_label = fields.Binary("Label", attachment=True)
    datas_fname = fields.Char("File name")

    @api.multi
    def action_cancel(self):
        for rec in self:
            rec.carrier_id.cancel_shipment(rec.picking_id)

    @api.multi
    def download_label(self):
        self.ensure_one()
        url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url += '/web/content/%s/%s/binary_label/%s?download=True' % (self._name, self.id, self.datas_fname)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': '_new',
        }


class ProductTemplateDeliveryTracking(models.Model):
    _inherit = 'product.template'

    delivery_ok = fields.Boolean("Is a delivery mode")


class StockQuantPackageDeliveryTracking(models.Model):
    _inherit = 'stock.quant.package'

    carrier_id = fields.Many2one('delivery.carrier', "Delivery Carrier")
    delivery_carrier_ok = fields.Boolean("Is a delivery Carrier Package")
    provider_id = fields.Many2one('delivery.carrier.provider', "Carrier", related='carrier_id.provider_id', store=True)


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    package_carrier_type = fields.Selection(selection_add=_PROVIDER)
    provider_id = fields.Many2one('delivery.carrier.provider', "Provider", compute='_compute_provider_id', store=True)

    @api.multi
    @api.depends('package_carrier_type')
    def _compute_provider_id(self):
        for rec in self:
            if rec.package_carrier_type != 'other':
                rec.provider_id = self.env['delivery.carrier.provider']._get_by_code(rec.package_carrier_type)
            else:
                provider_ids = self.env['delivery.carrier.provider']._get_by_code(rec.package_carrier_type)
                for provider in provider_ids:
                    if rec.name.endswith(provider.name):
                        rec.provider_id = provider


class DeliveryCarrierDeliveryTracking(models.Model):
    _inherit = 'delivery.carrier'

    provider_id = fields.Many2one('delivery.carrier.provider', "Carrier", compute='_compute_carrier_id', store=True)

    image = fields.Binary("Image", related='provider_id.image', store=True)
    product_id = fields.Many2one('product.product', string="Product", domain=[('delivery_ok', '=', True)])
    delivery_type = fields.Selection(selection_add=_PROVIDER)
    used_from_customer_ok = fields.Boolean("Can generate return label")
    used_to_customer_ok = fields.Boolean("Can generate send label")
    carrier_code = fields.Char("Carrier product code")

    tracking_count = fields.Integer("#Tracking", compute='_compute_number_related')
    sale_count = fields.Integer("#Sales", compute='_compute_number_related')
    package_count = fields.Integer("#Packages", compute='_compute_number_related')
    get_tracking_link_ok = fields.Boolean("Can get tracking link", related='provider_id.get_tracking_link_ok')
    cancel_shipment_ok = fields.Boolean("Can cancel tracking", related='provider_id.cancel_shipment_ok')
    rate_shipment_ok = fields.Boolean("Can rate shipment", related='provider_id.rate_shipment_ok')
    send_shipping_ok = fields.Boolean("Can send shipping", related='provider_id.send_shipping_ok')

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, " - ".join([name for name in [rec.provider_id.name, rec.name] if name])))
        return res

    @api.multi
    @api.depends('delivery_type')
    def _compute_carrier_id(self):
        for rec in self:
            if rec.delivery_type != 'other':
                rec.provider_id = self.env['delivery.carrier.provider']._get_by_code(rec.delivery_type)
            else:
                provider_ids = self.env['delivery.carrier.provider']._get_by_code(rec.delivery_type)
                for provider in provider_ids:
                    if rec.name.endswith(provider.name):
                        rec.provider_id = provider

    @api.multi
    def _compute_number_related(self):
        def _query(ids, model):
            fk = 'carrier_id'
            return {it[fk][0]: it['%s_count' % fk] for it in model.read_group([(fk, 'in', ids)], [fk], [fk]) if it[fk]}

        res_number = _query(self.ids, self.env['delivery.carrier.tracking.number'])
        res_sale = _query(self.ids, self.env['sale.order'])
        res_package = _query(self.ids, self.env['stock.quant.package'])

        for rec in self:
            rec.sale_count = res_sale.get(rec.id, 0)
            rec.tracking_count = res_number.get(rec.id, 0)
            rec.package_count = res_package.get(rec.id, 0)

    @api.model
    def _get_by_code(self, code):
        return self.search([('delivery_type', '=', code)])

    @api.multi
    def see_tracking_numbers(self):
        self.ensure_one()
        return self._see_related('delivery.carrier.tracking.number')

    @api.multi
    def see_sales(self):
        self.ensure_one()
        return self._see_related('sale.order')

    @api.multi
    def see_packages(self):
        self.ensure_one()
        return self._see_related('stock.quant.package')

    @api.multi
    def _see_related(self, related_name):
        self.ensure_one()
        return {
            'name': _t(self.env[related_name]._description),
            'type': 'ir.actions.act_window',
            'res_model': related_name,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('carrier_id', '=', self.id)],
            'context': dict(self.env.context, default_carrier_id=self.id)
        }


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    cancel_shipment_ok = fields.Boolean("Can cancel tracking", related='carrier_id.cancel_shipment_ok')

    @api.multi
    def save_tracking_number(self, name, datas):
        self.ensure_one()
        return self.env['delivery.carrier.tracking.number'].create({
            'name': name,
            'carrier_id': self.carrier_id.id,
            'picking_id': self.id,
            'binary_label': base64.encodebytes(datas),
            'datas_fname': "Colis %s.pdf" % name,
        })
