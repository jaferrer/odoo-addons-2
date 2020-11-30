# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def _get_product_accounts(self):
        self.ensure_one()
        res = super(ProductTemplate, self)._get_product_accounts()

        exp_account = self.property_account_expense_id
        if not exp_account:
            categ = self.categ_id
            while categ and not categ.property_account_expense_categ_id:
                categ = categ.parent_id
            exp_account = categ.property_account_expense_categ_id

        inc_account = self.property_account_income_id
        if not inc_account:
            categ = self.categ_id
            while categ and not categ.property_account_income_categ_id:
                categ = categ.parent_id
            inc_account = categ.property_account_income_categ_id

        res.update({
            'income': inc_account,
            'expense': exp_account,
        })
        return res
