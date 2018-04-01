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

from openerp.exceptions import UserError

from openerp import models, api, _


class BankStatementMerge(models.Model):
    _inherit = 'account.bank.statement'

    @api.multi
    def merge_statements(self):
        if any([item.state == 'confirm' for item in self]):
            raise UserError(_(u"It is forbidden to merge confirmed bank statements."))
        min_create_date = min([rec.create_date for rec in self])
        oldest_statement = self
        for rec in self:
            if rec.create_date == min_create_date:
                oldest_statement = rec
                break
        for rec in self:
            if rec != oldest_statement:
                rec.line_ids.write({'statement_id': oldest_statement.id})
                oldest_statement.balance_end_real = oldest_statement.balance_end_real + rec.balance_end_real - \
                    rec.balance_start
                rec.unlink()
