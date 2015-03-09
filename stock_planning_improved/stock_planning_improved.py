# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from datetime import datetime

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import fields, models, api


class procurement_order_planning_improved(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def action_reschedule(self):
        """Reschedules the moves associated to this procurement."""
        for proc in self:
            calendar_id, resource_id = proc._get_move_calendar()
            proc_date = datetime.strptime(proc.date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
            newdate = proc._schedule_working_days(-proc.rule_id.delay or 0, proc_date, resource_id, calendar_id)
            proc.move_ids.date = newdate


class stock_move_planning_improved(models.Model):
    _inherit = 'stock.move'

    date = fields.Datetime(string="Due Date", help="Due date for this stock move to be on schedule.")

    @api.multi
    def onchange_date(self, date, date_expected):
        """Remove link between date and date_expected since they are totally independent."""
        return {}
