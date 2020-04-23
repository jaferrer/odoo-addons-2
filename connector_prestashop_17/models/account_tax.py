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

from openerp.addons.connector_prestashop.models.account_tax.importer import AccountTaxImporter

from ..backend import prestashop_1_7


@prestashop_1_7
class AccountTaxImporterExtension(AccountTaxImporter):
    _model_name = 'prestashop.account.tax'
    _erp_field = 'amount'
    _ps_field = 'rate'

    def _compare_function(self, ps_val, erp_val, ps_dict, erp_dict):
        if (self.backend_record.taxes_included and not erp_dict['price_include']) or \
                (not self.backend_record.taxes_included and erp_dict['price_include']):
            return False
        return (erp_dict['type_tax_use'] == 'sale' and
                erp_dict['amount_type'] == 'percent' and
                abs(erp_val - float(ps_val)) < 0.01 and
                self.backend_record.company_id.id == erp_dict['company_id'][0])
