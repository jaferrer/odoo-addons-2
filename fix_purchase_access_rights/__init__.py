# -*- coding: utf8 -*-
#
# Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # TODO: overwritten fields purchase_order_count and supplier_invoice_count and their compute functions should be
    # TODO: removed after Odoo merged the corresponding NDP PR.

    @api.multi
    def _purchase_order_count(self):
        PurchaseOrder = self.env['purchase.order']
        for partner in self:
            partner.purchase_order_count = PurchaseOrder.search_count([('partner_id', 'child_of', partner.id)])

    @api.multi
    def _purchase_invoice_count(self):
        Invoice = self.env['account.invoice']
        for partner in self:
            partner.supplier_invoice_count = Invoice.search_count([('partner_id', 'child_of', partner.id),
                                                                   ('type', '=', 'in_invoice')])

    purchase_order_count = fields.Integer(compute='_purchase_order_count')
    supplier_invoice_count = fields.Integer(compute='_purchase_invoice_count')
