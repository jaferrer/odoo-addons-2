# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from odoo.addons.component.core import Component
from odoo.addons.connector_magento_catalog_manager.components.exceptions import BadConnectorAnswerException


class AccountInvoiceAdapter(Component):
    _inherit = 'magento.invoice.adapter'

    def create(self, order_increment_id, items, comment, email,
               include_comment):
        res = super(AccountInvoiceAdapter, self).create(order_increment_id, items, comment, email, include_comment)
        if not res.isdigit():
            raise BadConnectorAnswerException('order/%s/invoice' % order_increment_id, 'POST', res)
        return res
