# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    @api.one
    def compute(self, value, date_ref=False):
        result = super(AccountPaymentTerm, self).compute(value, date_ref=date_ref)[0]
        for i in range(len(self.line_ids)):
            line = self.line_ids[i]
            if line.option == 'configurable':
                next_date = (datetime.strptime(date_ref, '%Y-%m-%d') + relativedelta(days=line.days))
                if line.days2 < 0:
                    next_first_date = next_date + relativedelta(day=1, months=1)  # Getting 1st of next month
                    next_date = next_first_date + relativedelta(days=line.days2)
                if line.days2 > 0:
                    next_date += relativedelta(day=line.days2, months=1)
                result[i] = (next_date.strftime('%Y-%m-%d'), result[i][1])
        return result


class AccountPaymentTermLine(models.Model):
    _inherit = 'account.payment.term.line'

    option = fields.Selection(selection_add=[('configurable', u"Configurable")])
    days2 = fields.Integer(string=u"Day of the month",
                           help=u"Day of the month, set -1 for the last day of the current month. "
                                u"If it's positive, it gives the day of the next month. "
                                u"Set 0 for net days (otherwise it's based on the beginning of the month).")
