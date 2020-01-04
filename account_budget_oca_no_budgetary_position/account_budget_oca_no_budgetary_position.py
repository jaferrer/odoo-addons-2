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


from odoo import models, fields, api


class NbpCrossoveredBudgetLines(models.Model):
    _inherit = 'crossovered.budget.lines'

    general_budget_id = fields.Many2one('account.budget.post', required=False)
    analytic_account_id = fields.Many2one('account.analytic.account', required=True)

    @api.multi
    def _compute_practical_amount(self):
        # The practical amount should not be filtered on budgetary position accounts
        for line in self:
            result = 0.0
            date_to = line.date_to
            date_from = line.date_from
            if line.analytic_account_id.id:
                self.env.cr.execute(
                    """
                    SELECT SUM(amount)
                    FROM account_analytic_line
                    WHERE account_id=%s
                        AND (date BETWEEN %s AND %s)""",
                    (line.analytic_account_id.id, date_from, date_to,)
                )
                result = self.env.cr.fetchone()[0] or 0.0
            line.practical_amount = result
