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
#

from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    win_reason = fields.Many2one('crm.win.reason', string=u"Win reason")

    @api.multi
    def action_set_won_with_reason(self):
        wiz = self.env['crm.lead.win'].create({})
        return {
            'Name': u"Win reason",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'crm.lead.win',
            'target': 'new',
            'res_id': wiz.id
        }


class CrmWinReason(models.Model):
    _name = 'crm.win.reason'

    name = fields.Char(u"Name", required=True, translate=True)
    active = fields.Boolean(u"Active", default=True)


class CrmLeadWin(models.TransientModel):
    _name = 'crm.lead.win'

    win_reason_id = fields.Many2one('crm.win.reason', string=u"Win reason")

    @api.multi
    def action_win_reason_apply(self):
        leads = self.env['crm.lead'].browse(self.env.context.get('active_ids'))
        leads.write({'win_reason': self.win_reason_id.id})
        return leads.action_set_won_rainbowman()
