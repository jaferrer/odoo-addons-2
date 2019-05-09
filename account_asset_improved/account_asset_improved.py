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

from openerp import models, fields, api


class AccountAssetCategoryImproved(models.Model):
    _inherit = 'account.asset.category'

    account_moves_end_fiscalyear = fields.Boolean(string=u"End fiscalyear moves")


class AccountAssetAssetImproved(models.Model):
    _inherit = 'account.asset.asset'

    account_moves_end_fiscalyear = fields.Boolean(string=u"End fiscalyear moves")

    def onchange_category_id_values(self, category_id):
        result = super(AccountAssetAssetImproved, self).onchange_category_id_values(category_id)
        if category_id:
            category = self.env['account.asset.category'].browse(category_id)
            result = result or {}
            result['value'] = result.get('value', {})
            result['value']['account_moves_end_fiscalyear'] = category.account_moves_end_fiscalyear
        return result


class AccountAssetDepreciationLineImproved(models.Model):
    _inherit = 'account.asset.depreciation.line'

    @api.model
    def create(self, vals):
        depreciation_date = vals.get('depreciation_date')
        asset = self.env['account.asset.asset'].browse(vals['asset_id'])
        if depreciation_date and asset.method_time == 'number' and asset.account_moves_end_period:
            vals['depreciation_date'] = asset.company_id. \
                compute_fiscalyear_dates(fields.Date.from_string(depreciation_date))['date_to']
        return super(AccountAssetDepreciationLineImproved, self).create(vals)
