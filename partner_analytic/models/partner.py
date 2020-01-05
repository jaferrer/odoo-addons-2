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


class ResPartner(models.Model):
    _inherit = 'res.partner'

    income_analytic_account_id = fields.Many2one('account.analytic.account', string='Income Analytic Account')
    expense_analytic_account_id = fields.Many2one('account.analytic.account', string='Expense Analytic Account')

    @api.multi
    def _get_partner_analytic_accounts(self):
        if not self:
            return {}
        self.ensure_one()
        return {
            'income': self.income_analytic_account_id or self.env['account.analytic.account'],
            'expense': self.expense_analytic_account_id or self.env['account.analytic.account'],
        }
