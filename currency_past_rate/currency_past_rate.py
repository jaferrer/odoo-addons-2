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

from openerp import models, api, exceptions, _


class ResCurrencyPastRate(models.Model):
    _inherit = 'res.currency'

    @api.multi
    def get_rate_at_date(self, date):
        self.ensure_one()
        last_rate_before_date = self.env['res.currency.rate'].search([('currency_id', '=', self.id),
                                                                      ('name', '<=', date)], order='name desc', limit=1)
        if not last_rate_before_date:
            raise exceptions.except_orm(_(u"Error!"), _(u"No currency rate found for currency %s before date %s") %
                                        (self.display_name, date))
        return last_rate_before_date.rate
