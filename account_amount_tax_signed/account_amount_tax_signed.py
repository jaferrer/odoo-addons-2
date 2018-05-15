# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    amount_tax_signed = fields.Monetary(string=u"Taxes amount", currency_field='currency_id',
                                        help=u"This amount can be negative",
                                        compute='_compute_amount_tax_signed', store=True, readonly=True)

    @api.depends('amount_total_signed', 'amount_untaxed_signed')
    @api.multi
    def _compute_amount_tax_signed(self):
        for rec in self:
            rec.amount_tax_signed = rec.amount_total_signed - rec.amount_untaxed_signed
