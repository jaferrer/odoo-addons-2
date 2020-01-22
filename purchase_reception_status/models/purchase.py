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


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    reception_status = fields.Selection([('no', u"Not received"), ('partial', u"Partially Received"),
                                         ('yes', u"Received")], string=u"Reception Status", store=True,
                                        compute='_compute_reception_status')

    @api.multi
    @api.depends('order_line', 'order_line.qty_received', 'order_line.product_qty')
    def _compute_reception_status(self):
        for rec in self:
            partial = False
            full = True
            for line in rec.order_line:
                if line.qty_received >= line.product_qty:
                    if full:
                        continue
                full = False
                if line.qty_received > 0:
                    partial = True
                    break
            if partial:
                rec.reception_status = 'partial'
                continue
            if full:
                rec.reception_status = 'yes'
                continue
            rec.reception_status = 'no'
