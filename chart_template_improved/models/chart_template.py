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

from odoo import models, api


class ChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.multi
    def generate_properties(self, acc_template_ref, company):
        """ This method used for creating properties.

        copied from account/models/chart_template.py l.212
        This override aims to fix an unwanted behaviour that prevented the creation of the "general" ir.properties
        when record-specific ir.properties (ie ir.property with res_id != null) already existed in the table.

        :param self: chart templates for which we need to create properties
        :param acc_template_ref: Mapping between ids of account templates and real accounts created from them
        :param company: company_id selected from wizard.multi.charts.accounts.
        :returns: True
        """
        self.ensure_one()
        property_obj = self.env['ir.property']
        todo_list = [
            ('property_account_receivable_id', 'res.partner', 'account.account'),
            ('property_account_payable_id', 'res.partner', 'account.account'),
            ('property_account_expense_categ_id', 'product.category', 'account.account'),
            ('property_account_income_categ_id', 'product.category', 'account.account'),
            ('property_account_expense_id', 'product.template', 'account.account'),
            ('property_account_income_id', 'product.template', 'account.account'),
        ]
        for record in todo_list:
            account = getattr(self, record[0])
            value = account and 'account.account,' + str(acc_template_ref[account.id]) or False
            if value:
                field = self.env['ir.model.fields'].search([
                    ('name', '=', record[0]),
                    ('model', '=', record[1]),
                    ('relation', '=', record[2])
                ], limit=1)
                vals = {
                    'name': record[0],
                    'company_id': company.id,
                    'fields_id': field.id,
                    'value': value,
                }
                # Braine => Here, we add a constraint on res_id, to ignore record-specific properties
                properties = property_obj.search([
                    ('name', '=', record[0]),
                    ('company_id', '=', company.id),
                    ('res_id', '=', False)
                ])
                if properties:
                    # the property exist: modify it
                    properties.write(vals)
                else:
                    # create the property
                    property_obj.create(vals)
        stock_properties = [
            'property_stock_account_input_categ_id',
            'property_stock_account_output_categ_id',
            'property_stock_valuation_account_id',
        ]
        for stock_property in stock_properties:
            account = getattr(self, stock_property)
            value = account and acc_template_ref[account.id] or False
            if value:
                company.write({stock_property: value})
        return True
