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

import logging

from odoo import api, fields, models, exceptions, _

_logger = logging.getLogger(__name__)


class AccountAccountForceReconcile(models.Model):
    _inherit = 'account.account'

    @api.multi
    def open_force_reconcile_wizard(self):
        ctx = dict(self.env.context)
        ctx['default_account_ids'] = [(6, 0, self.env.context.get('active_ids', []))]
        return {
            'name': _(u"Force set accounts to reconcilable"),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.account.force.reconciliable',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def write(self, vals):
        vals_save = vals.copy()
        for rec in self:
            if vals.get('reconcile') and vals['reconcile'] == rec.reconcile:
                del(vals_save['reconcile'])
                return super(AccountAccountForceReconcile, rec).write(vals_save)
        return super(AccountAccountForceReconcile, self).write(vals)


class WizardSetAccountReconciliable(models.TransientModel):
    _name = 'account.account.force.reconciliable'

    account_ids = fields.Many2many('account.account', string=u"Accounts", required=True)

    @api.multi
    def set_reconciliable(self):
        self.ensure_one()
        nb_accounts = len(self.account_ids)
        index_accounts = 0
        for account in self.account_ids:
            index_accounts += 1
            _logger.info(u"Setting account %s to reconciliable (%s/%s)",
                         account.display_name, index_accounts, nb_accounts)
            if account.reconcile:
                continue
            try:
                account.reconcile = True
            except exceptions.UserError:
                self.env.cr.execute("""UPDATE account_account set reconcile = TRUE WHERE ID = %s""", (account.id,))
                self.env.invalidate_all()
                move_lines_to_process = self.env['account.move.line'].search([('account_id', '=', account.id)])
                nb_move_lines = len(move_lines_to_process)
                index_move_lines = 0
                for move_line in move_lines_to_process:
                    index_move_lines += 1
                    _logger.info(u"Recomputing fields for move line %s, ID=%s (%s/%s)",
                                 move_line.display_name, move_line.id, index_move_lines, nb_move_lines)
                    move_line._amount_residual()
