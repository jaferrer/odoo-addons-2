# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    categ_id = fields.Many2one('product.category', related='product_id.categ_id', store=True, readonly=True,
                               string=u"Internal Category")
    pos_categ_id = fields.Many2one('pos.category', related='product_id.pos_categ_id', store=True, readonly=True,
                                   string=u"Point of Sale Category")
    date_order = fields.Datetime(related='order_id.date_order', store=True, readonly=True, string=u"Order Date")
    state = fields.Selection([('draft', 'New'),
                              ('cancel', 'Cancelled'),
                              ('paid', 'Paid'),
                              ('done', 'Posted'),
                              ('invoiced', 'Invoiced')],
                             related='order_id.state', store=True, readonly=True, string=u"Order Status")
    price_subtotal = fields.Float(store=True)
    price_subtotal_incl = fields.Float(store=True)
