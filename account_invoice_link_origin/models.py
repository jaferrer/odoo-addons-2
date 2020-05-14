# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import api, fields, models


class AccountInvoiceLinkOrigin(models.Model):
    _inherit = 'account.invoice'

    origin_sale_order_id = fields.Many2one('sale.order', string=u"Sale order", readonly=True)
    origin_purchase_order_id = fields.Many2one('purchase.order', string=u"Purchase order", readonly=True)

    @api.model
    def create(self, vals):
        if 'origin' in vals:
            so = self.env['sale.order'].search([('name', '=', vals['origin'])], limit=1)
            if so:
                vals['origin_sale_order_id'] = so.id
            po = self.env['purchase.order'].search([('name', '=', vals['origin'])], limit=1)
            if po:
                vals['origin_purchase_order_id'] = po.id

        return super(AccountInvoiceLinkOrigin, self).create(vals)
