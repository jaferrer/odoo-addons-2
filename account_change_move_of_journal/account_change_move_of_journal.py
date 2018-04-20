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
#

from openerp import models, fields, api, _


class AccountChangeMove(models.Model):
    _inherit = 'account.move'

    @api.multi
    def change_move_of_journal(self):
        return {
            'name': _(u"Change account move of journal"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.change.move.journal',
            'target': 'new',
            'context': dict(self.env.context),
        }


class AccountChangeMoveJournal(models.TransientModel):
    _name = 'account.change.move.journal'

    date = fields.Date(string=u"Force date for new moves",
                       help=u"If this field is not set, we will use the same date as initial moves")
    journal_id = fields.Many2one('account.journal', string=u"New journal", required=True)

    @api.multi
    def execute(self):
        self.ensure_one()
        moves = self.env['account.move'].search([('id', 'in', self.env.context.get('active_ids', []))])
        display_move_ids = moves.ids
        for move in moves:
            if move.journal_id != self.journal_id:
                display_move_ids += move.reverse_moves(self.date or move.date, move.journal_id or False)
                display_move_ids += move.copy({'date': self.date or move.date, 'journal_id': self.journal_id.id}).ids
        return {
            'name': _(u"Generated account moves"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', display_move_ids)],
            'context': dict(self.env.context),
        }
