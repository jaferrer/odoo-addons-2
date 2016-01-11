# -*- coding: utf8 -*-
#
# Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
import openerp.addons.decimal_precision as dp


class AcountNegativeAmount(models.Model):
    _inherit = "account.invoice"

    amount_untaxed_neg_if_refund = fields.Float(string='Subtotal', digits=dp.get_precision('Account'),
                                                store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_total_neg_if_refund = fields.Float(string='Total', digits=dp.get_precision('Account'),
                                              store=True, readonly=True, compute='_compute_amount')
    residual_neg_if_refund = fields.Float(string='Balance', digits=dp.get_precision('Account'),
                                          compute='_compute_residual', store=True,
                                          help="Remaining amount due.")

    @api.one
    def _compute_amount(self):
        super(AcountNegativeAmount, self)._compute_amount()
        if self.type in ('out_refund', 'in_refund'):
            self.amount_untaxed_neg_if_refund = self.amount_untaxed * -1
            self.amount_total_neg_if_refund = self.amount_total * -1
        else:
            self.amount_untaxed_neg_if_refund = self.amount_untaxed
            self.amount_total_neg_if_refund = self.amount_total

    @api.one
    def _compute_residual(self):
        super(AcountNegativeAmount, self)._compute_residual()

        if self.type in ('out_refund', 'in_refund'):
            self.residual_neg_if_refund = self.residual * -1
        else:
            self.residual_neg_if_refund = self.residual
