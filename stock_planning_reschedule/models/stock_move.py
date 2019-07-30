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

from odoo import api, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def write(self, vals):
        """Write function overridden to propagate date to previous procurement orders
        and assign user who has transferred the move"""
        for rec in self:
            if vals.get('date') and vals.get('state') != 'done' and rec.procure_method == 'make_to_order':
                # If the date is changed and moves are chained, propagate to the previous procurement if any
                proc = self.env['procurement.order'].search([
                    ('move_dest_id', '=', rec.id),
                    ('state', 'not in', ['done', 'cancel']),
                ], limit=1)
                if proc and not self.env.context.get('do_not_propagate_rescheduling'):
                    proc.date_planned = vals.get('date')
                    proc.action_reschedule()

        return super(StockMove, self).write(vals)
