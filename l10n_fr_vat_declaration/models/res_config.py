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

from openerp import models, fields


class VatDeclarationConfig(models.TransientModel):
    _inherit = 'account.config.settings'

    journal_for_vat_declarations_id = fields.Many2one('account.journal', string=u"Default journal for VAT declarations",
                                                      related='company_id.journal_for_vat_declarations_id')
    account_vat_to_pay_id = fields.Many2one('account.account', string=u"Account for VAT to pay",
                                            related='company_id.account_vat_to_pay_id')
