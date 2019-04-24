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

from openerp import models, fields, api, exceptions, _


class VatDeclarationGenerator(models.TransientModel):
    _name = 'vat.declaration.generator'

    def _get_default_journal_for_vat_declarations_id(self):
        return self.env.user.company_id.journal_for_vat_declarations_id

    def _get_default_account_vat_to_pay_id(self):
        return self.env.user.company_id.account_vat_to_pay_id

    def _get_default_customer_tax_account_ids(self):
        taxes = self.env['account.tax'].search(['|', '&', ('type_tax_use', '=', 'sale'),
                                                ('amount', '>', 0),
                                                '&', ('type_tax_use', '=', 'purchase'),
                                                ('amount', '<', 0)])
        accounts = self.env['account.account']
        for tax in taxes:
            accounts |= tax.account_id
        return accounts

    def _get_default_supplier_tax_account_ids(self):
        taxes = self.env['account.tax'].search(['|', '&', ('type_tax_use', '=', 'purchase'),
                                                ('amount', '>', 0),
                                                '&', ('type_tax_use', '=', 'sale'),
                                                ('amount', '<', 0)])
        accounts = self.env['account.account']
        for tax in taxes:
            accounts |= tax.account_id
        return accounts

    date_start = fields.Date(string=u"Start period date")
    date_end = fields.Date(string=u"End period date", required=True)
    journal_for_vat_declarations_id = fields.Many2one('account.journal', string=u"Journal for VAT declaration",
                                                      required=True,
                                                      default=_get_default_journal_for_vat_declarations_id)
    account_vat_to_pay_id = fields.Many2one('account.account', string=u"Account for VAT to pay", required=True,
                                            default=_get_default_account_vat_to_pay_id)
    customer_tax_account_ids = fields.Many2many('account.account', 'vat_generator_customer_tax_rel',
                                                'account_account_id', 'vat_declaration_generator_id',
                                                string=u"Customer taxes accounts",
                                                default=_get_default_customer_tax_account_ids)
    supplier_tax_account_ids = fields.Many2many('account.account', 'vat_generator_supplier_tax_rel',
                                                'account_account_id', 'vat_declaration_generator_id',
                                                string=u"Supplier taxes accounts",
                                                default=_get_default_supplier_tax_account_ids)

    @api.multi
    def get_vat_to_pay(self):
        self.ensure_one()
        total_vat_to_pay = 0
        line_vals = []
        move_lines_to_pay_before_date_end = self.env['account.move.line']. \
            search([('account_id', 'in', self.customer_tax_account_ids.ids),
                    ('date', '<=', self.date_end),
                    ('move_id.state', '=', 'posted')])
        dict_vat_to_pay = move_lines_to_pay_before_date_end.get_total_balance_by_account()

        for account_vat_to_pay_id in dict_vat_to_pay:
            vat_to_pay = dict_vat_to_pay[account_vat_to_pay_id]
            if abs(vat_to_pay) < 0.001:
                continue
            total_vat_to_pay += vat_to_pay
            line_vals += [(0, 0, {
                'date_maturity': self.date_end,
                'account_id': account_vat_to_pay_id,
                'debit': vat_to_pay,
                'credit': 0,
                'name': u"Test",
            })]
        return line_vals, total_vat_to_pay

    @api.multi
    def get_vat_to_deduce(self, line_vals, total_vat_to_pay):
        self.ensure_one()
        move_lines_to_deduce_before_date_end = self.env['account.move.line']. \
            search([('account_id', 'in', self.supplier_tax_account_ids.ids),
                    ('date', '<=', self.date_end),
                    ('move_id.state', '=', 'posted')])
        dict_vat_to_deduce = move_lines_to_deduce_before_date_end.get_total_balance_by_account()
        for account_vat_to_deduce_id in dict_vat_to_deduce:
            vat_to_deduce = dict_vat_to_deduce[account_vat_to_deduce_id] * (-1)
            if abs(vat_to_deduce) < 0.001:
                continue
            total_vat_to_pay -= vat_to_deduce
            line_vals += [(0, 0, {
                'date_maturity': self.date_end,
                'account_id': account_vat_to_deduce_id,
                'debit': 0,
                'credit': vat_to_deduce,
                'name': u"Test",
            })]
        return line_vals, total_vat_to_pay

    @api.multi
    def get_final_vat_line(self, line_vals, total_vat_to_pay):
        self.ensure_one()
        if abs(total_vat_to_pay) > 0.001:
            line_vals += [(0, 0, {
                'date_maturity': self.date_end,
                'account_id': self.account_vat_to_pay_id.id,
                'debit': 0,
                'credit': total_vat_to_pay,
                'name': u"Test",
            })]
        return line_vals

    @api.multi
    def generate_account_move(self):
        self.ensure_one()
        line_vals, total_vat_to_pay = self.get_vat_to_pay()
        line_vals, total_vat_to_pay = self.get_vat_to_deduce(line_vals, total_vat_to_pay)
        if total_vat_to_pay < 0.001:
            raise exceptions.UserError(u"Aucune TVA à facturer")
        line_vals = self.get_final_vat_line(line_vals, total_vat_to_pay)
        account_move = self.env['account.move']. \
            create({
            'date': self.date_end,
            'journal_id': self.journal_for_vat_declarations_id.id,
            'line_ids': line_vals,
        })
        return {
            'name': _(u"VAT Declaration move"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': account_move.id,
            'context': self.env.context,
        }


class VatDeclarationMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.multi
    def get_total_balance_by_account(self):
        move_lines_read = self.read(['id', 'debit', 'credit', 'account_id'], load=False)
        total_balance_by_account = {}
        for move_line in move_lines_read:
            vat_to_pay = move_line['credit'] - move_line['debit']
            if move_line['account_id'] not in total_balance_by_account:
                total_balance_by_account[move_line['account_id']] = 0
            total_balance_by_account[move_line['account_id']] += vat_to_pay
        return total_balance_by_account
