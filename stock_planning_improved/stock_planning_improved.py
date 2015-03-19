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
import time

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import fields, models, api


class procurement_order_planning_improved(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def action_reschedule(self):
        """Reschedules the moves associated to this procurement."""
        for proc in self:
            if proc.state not in ['done', 'cancel'] and proc.rule_id and proc.rule_id.action == 'move':
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

    @api.multi
    def action_done(self):
        """ Process completely the moves given as ids and if all moves are done, it will finish the picking.
        Overridden here not to modify date_expected.
        """
        dates = dict([(m.id, m.date) for m in self])
        super(stock_move_planning_improved, self).action_done()
        for move in self:
            move.write({
                'date': dates[move.id],
                'date_expected': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            })

    @api.multi
    def write(self, vals):
        """Write function overridden to propagate date to previous procurement orders."""
        for move in self:
            if vals.get('date') and move.procure_method == 'make_to_order':
                proc = self.env['procurement.order'].search([('move_dest_id','=',move.id),
                                                             ('state','not in',['done','cancel'])], limit=1)
                if proc:
                    proc.date_planned = vals.get('date')
                    proc.action_reschedule()
        return super(stock_move_planning_improved, self).write(vals)


class stock_picking_planning_improved(models.Model):
    _inherit = 'stock.picking'

    date_due = fields.Datetime("Due Date", compute="_compute_date_due", store=True,
                               help="Date before which the first moves of this picking must be made so as not to be "
                                    "late on schedule.")

    @api.depends('move_lines.date')
    def _compute_date_due(self):
        if not self.ids:
            return
        cr = self.env.cr
        cr.execute("""select
            picking_id,
            min(date)
        from
            stock_move
        where
            picking_id IN %s
        group by
            picking_id""", (tuple(self.ids),))
        dates = dict(cr.fetchall())
        for picking in self:
            picking.date_due = dates.get(picking.id, False)
