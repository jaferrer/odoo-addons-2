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

from openerp import models, api

_logger = logging.getLogger(__name__)


class AccountVoucher(models.Model):
    _inherit = 'account.voucher'

    @api.multi
    def proforma_voucher(self):
        res = super(AccountVoucher, self).proforma_voucher()
        self.invoice_id.on_new_payment()
        return res
