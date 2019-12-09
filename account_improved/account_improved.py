# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.multi
    @api.depends('line_id', 'line_id.credit', 'line_id.debit')
    def _compute_is_balanced(self):
        prec = self.env['decimal.precision'].precision_get('Account')
        for rec in self:
            amount = 0
            for line in rec.line_id:
                amount += line.debit - line.credit
            rec.is_balanced = round(abs(amount), prec) < 10 ** (-max(5, prec))

    is_balanced = fields.Boolean(compute='_compute_is_balanced', string=u"Is balanced", store=True)
