# -*- coding: utf8 -*-
#
#    Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class cofinex_crm_phonecall(models.Model):
    _inherit = 'crm.phonecall'

    type_action = fields.Selection([('call', _("Call")), ('email', _("E-mail")), ('reminder', _("Reminder")),
                                    ('appointment', _("Appointment"))], string="Type of action",
                                   default='call', index=True)

    @api.multi
    def open_phonecall(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.phonecall',
            'name': _("Action"),
            'views': [(False, "form")],
            'res_id': self.id,
            'context': {}
        }
