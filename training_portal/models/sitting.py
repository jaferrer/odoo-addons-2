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

from odoo import models, _


class TrainingSitting(models.Model):
    _inherit = 'training.sitting'

    def manage_portal_access(self):
        attendees = self.env['res.partner']
        for rec in self:
            attendees |= rec.attendee_ids
        if not attendees:
            return
        ctx = dict(self.env.context)
        portal_user_ids = []
        for attendee in attendees:
            portal_user_ids += [(0, 0, {'partner_id': attendee.id,
                                        'email': attendee.email,
                                        'in_portal': True})]
        ctx['default_user_ids'] = portal_user_ids
        return {
            'name': _("Grant portal access"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'portal.wizard',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }
