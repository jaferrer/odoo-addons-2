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

from dateutil import relativedelta

from odoo import api, fields, models


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def action_reschedule(self):
        """Reschedules the moves associated to this procurement."""
        for rec in self:
            if rec.state not in ['done', 'cancel'] and rec.rule_id and rec.rule_id.action == 'move':
                new_date = fields.Datetime.from_string(rec.date_planned) + relativedelta.relativedelta(
                    days=-self.rule_id.delay)
                vals = {
                    'date': new_date,
                    'date_expected': new_date
                }
                # We do not write in moves which dest loc is not the same as the procurement's location
                # (ex: return moves, which are linked to the same procurements as the original ones)
                self.env['stock.move'].search([
                    ('procurement_id', '=', rec.id),
                    ('location_dest_id', '=', rec.location_id.id),
                    '|',
                    ('date', '!=', fields.Datetime.to_string(new_date)),
                    ('date_expected', '!=', fields.Datetime.to_string(new_date)),
                ]).write(vals)
