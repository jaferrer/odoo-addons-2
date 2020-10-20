# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    ligne_compte_tiers_avec_facture = fields.Boolean(string=u"Has a third party line of account with an invoice",
                                        help=u"If the account is in type : payable, receivable, liquidity or staff",
                                        compute="_get_ligne_compte_tiers_avec_facture", readonly=True)
    reimputation = fields.Boolean(string=u"Is in re-allocate : Enter your final journal entries, all lines of the "
                                         u"previous journal entry will be reversed (offline third party account)")
    original_account_move_id = fields.Many2one('account.move', string=u"Original account move")
    extourne_parent_id = fields.Many2one('account.move', string=u"Reversal account move")
    reimputation_parent_id = fields.Many2one('account.move', string=u"Re-allocate account move")
    change_date_reimputation = fields.Boolean(
        string=u"Accounting date of the change is different from that of the original posting")

    @api.multi
    @api.depends('line_id', 'line_id.compte_tiers_avec_facture')
    def _get_ligne_compte_tiers_avec_facture(self):
        for rec in self:
            rec.ligne_compte_tiers_avec_facture = [True for l in rec.line_id if l.compte_tiers_avec_facture] or False

    @api.multi
    def extourner(self):

        def _inverse_line(line):
            line2 = line.copy()
            line2.update({
                'debit': line2['credit'],
                'credit': line2['debit'],
            })
            return line2

        self.ensure_one()
        copy_data = self.copy_data()[0]
        context = self.env.context.copy()
        context.update({
            'form_title': _("Reversal the accounting entry"),
            'default_extourne_parent_id': self.id,
            'default_name': u"EXT/" + self.name,
            'default_journal_id': copy_data.get('journal_id'),
            'default_period_id': copy_data.get('period_id'),
            'default_partner_id': copy_data.get('partner_id'),
            'default_company_id': self.company_id.id,
            'default_ref': self.ref,
            'default_date': copy_data.get('date'),
            'default_to_check': True,
            'default_line_id': [(lambda l:(0, 0, _inverse_line(l[2])))(line) for line in copy_data.get('line_id')],
        })
        return self.return_account_move_form(context)

    @api.model
    def create(self, vals):
        if vals.get('reimputation', False):
            to_reimpute = self.default_get(["original_account_move_id"]).get('original_account_move_id', False)
            name = self.default_get(["name"]).get('name', vals.get("reference", ""))
            vals.update({'line_id': self.generate_reimputation_lines(to_reimpute, vals.get('line_id', False)),
                         'reimputation': False, 'name': u"REI/" + name, 'original_account_move_id': to_reimpute})
        new_account_move = super(AccountMove, self).create(vals)
        new_account_move.reimputation = False
        return new_account_move

    def return_account_move_form(self, context_vars):
        form = self.env.ref('account.view_move_form', False)
        return {
            'name': context_vars.get("form_title", _("Accounting entry")),
            'view_mode': 'tree,form',
            'view_id': form.id,
            'view_type': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'flags': {'form': {'action_buttons': True}},
            'views': [(False, 'form')],
            'context': context_vars
        }

    @api.model
    def generate_reimputation_lines(self, original_account_move_id, new_list_lines):
        today = fields.Date.today()
        original_account_move = self.search([('id', '=', original_account_move_id)])
        change_date = original_account_move.period_id.state == 'done' and today or False
        for new_list_line in new_list_lines:
            new_line = new_list_line[2]
            new_line.update({'date': change_date or new_line.get('date_maturity', False)})
            if new_line.get('compte_tiers_avec_facture', False) and new_line.get("reimputation", False):
                new_list_lines.remove(new_list_line)
        # inverse of the original move
        for line in original_account_move.line_id:
            if not line.compte_tiers_avec_facture:
                new_key = len(new_list_lines) + 1
                inverse_line = line.copy_data()[0]
                date = change_date or line.date_maturity
                inverse_line.update(
                    {'debit': line.credit, 'credit': line.debit, 'date': date, 'tax_amount': (line.tax_amount * -1)})
                new_list_lines.append([0, new_key, inverse_line])
        return new_list_lines

    @api.multi
    def re_imputer(self):
        self.ensure_one()
        copy_data = self.copy_data()[0]
        context = self.env.context.copy()
        today = fields.Date.today()
        change_date = self.period_id.state == 'done' and today or False
        context.update({
            'form_title': _("Re-allocate the accounting entry"),
            'default_reimputation': True,
            'default_original_account_move_id': self.id,
            'default_reimputation_parent_id': self.id,
            'default_name': self.name,
            'default_journal_id': copy_data.get('journal_id'),
            'default_period_id': copy_data.get('period_id'),
            'default_partner_id': copy_data.get('partner_id'),
            'default_company_id': self.company_id.id,
            'default_ref': self.ref,
            'default_change_date_reimputation': bool(change_date),
            'default_date': fields.Date.to_string(change_date) or copy_data.get('date'),
            'default_line_id': copy_data.get('line_id'),
        })
        return self.return_account_move_form(context)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self.env.context.get('search_for_children'):
            nb_items = len(args)
            for index in range(nb_items):
                if args[index][0] == 'partner_id':
                    if args[index][1] in ['=', 'in']:
                        args[index][1] = 'child_of'
        return super(AccountMove, self).search(args, offset=offset, limit=limit, order=order, count=count)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    compte_tiers_avec_facture = fields.Boolean(
        string=u"Third party line of account with an invoice", compute="_get_compte_tiers_avec_facture")
    reimputation = fields.Boolean(string=u"Is in re-allocate", related="move_id.reimputation")

    @api.multi
    @api.depends('account_id', 'account_id.type')
    def _get_compte_tiers_avec_facture(self):
        for rec in self:
            rec.compte_tiers_avec_facture = \
                rec.account_id.type in ('payable', 'receivable', 'liquidity', 'staff') and rec.invoice
