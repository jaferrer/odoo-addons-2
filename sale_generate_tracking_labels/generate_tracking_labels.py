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

from openerp import models, api, fields


class GenerateTrackingLabelsWizard(models.TransientModel):
    _inherit = 'generate.tracking.labels.wizard'

    sale_order_id = fields.Many2one('sale.order', u"Commande client")

    @api.multi
    def _trigger_onchange(self):
        self.ensure_one()
        self.onchange_sale_order_id()
        return super(GenerateTrackingLabelsWizard, self)._trigger_onchange()

    @api.onchange('sale_order_id')
    def onchange_sale_order_id(self):
        self.ensure_one()
        if self.sale_order_id:
            self.partner_id = self.sale_order_id.partner_shipping_id
            self.weight = sum([l.product_id.weight * l.product_uom_qty for l in self.sale_order_id.order_line]) or 1
            self.transportation_amount = (self.sale_order_id and int(self.sale_order_id.amount_total)) or 0
            self.total_amount = (self.sale_order_id and int(self.sale_order_id.amount_untaxed)) or 0
            self.sender_parcel_ref = (self.sale_order_id and self.sale_order_id.name) or ''
            self.partner_orig_id = self.sale_order_id.warehouse_id.partner_id

    @api.multi
    def get_packages_data(self):
        self.ensure_one()
        if self.sale_order_id:
            return [{
                'weight': self.weight or 0,
                'amount_untaxed': self.sale_order_id.amount_untaxed or 0,
                'amount_total': self.sale_order_id.amount_total or 0,
                'cod_value': self.cod_value or 0,
                'height': 0,
                'lenght': 0,
                'width': 0,
            }]
        return super(GenerateTrackingLabelsWizard, self).get_packages_data()

    @api.multi
    def get_order_number(self):
        self.ensure_one()
        return self.sale_order_id.name or super(GenerateTrackingLabelsWizard, self).get_order_number()

