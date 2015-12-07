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

from openerp import fields, models, api


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    remaining_subtotal_cur = fields.Float(
        string=u"remaining subtotal devise local", compute='_compute_subtotal_cur', store=True, default=0)

    @api.depends('price_unit', 'remaining_qty')
    def _compute_subtotal_cur(self):
        for rec in self:
            line_price = self._calc_line_base_price(rec)
            cur = rec.order_id.pricelist_id.currency_id
            company_cur = self.env.user.company_id.currency_id
            remaining = rec.order_id.currency_id.with_context(date=rec.order_id.date_order).compute(
                cur.round(line_price * rec.remaining_qty), company_cur, round=True)
            rec.remaining_subtotal_cur = remaining
