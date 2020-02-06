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
#    along with this
#


import logging
from openerp import fields, models, api

_logger = logging.getLogger(__name__)


class ResPartnerBank(models.Model):
    _inherit = ['res.partner.bank']

    factor_email = fields.Char(u"Factor email")
    factor_cga_account_number = fields.Char(u"CGA account number")
    factor_contract_number = fields.Char(u"CGA contract number", default="001")
    factor_company_code = fields.Integer(u"Bank company code")
    factor_account_number = fields.Char(u"Bank account number")
    factor_contract_type = fields.Char(u"Bank contract type", default="D")
    factor_currency_id = fields.Many2one('res.currency', string=u"Bank Currency")

    @api.model
    def get_factor_settings_errors(self):
        self.ensure_one()
        mandatory_fields = ['factor_email', 'factor_cga_account_number', 'factor_contract_number',
                            'factor_company_code', 'factor_account_number', 'factor_contract_type',
                            'factor_currency_id']
        errors = []
        for field in mandatory_fields:
            if not self[field]:
                errors.append(u"%s must be set" % self._fields[field].string)
        return errors
