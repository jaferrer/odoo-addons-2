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
from openerp import fields, models, api, exceptions, _


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
    def write(self, vals):
        """Write function overridden to propagate date to previous procurement orders."""
        for move in self:
            if vals.get('date') and vals.get('state') == 'done':
                # If the call is made from action_done, don't change the (required) date, but only the date_expected
                vals['date_expected'] = vals['date']
                del vals['date']
            if vals.get('date') and move.procure_method == 'make_to_order':
                # If the date is changed and moves are chained, propagate to the previous procurement if any
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

    @api.multi
    def action_assign(self):
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        Overridden here to check only moves with available quants in source location.
        @return: True
        """
        for pick in self:
            if pick.state == 'draft':
                pick.action_confirm()
            #skip the moves that don't need to be checked
            moves = pick.move_lines.filtered(lambda m:
                                             m.state not in ('draft', 'cancel', 'done') and m.availability > 0.0)
            if not moves:
                raise exceptions.except_orm(_('Warning!'), _('Nothing to check the availability for.'))
            moves.action_assign()
        return True

    @api.multi
    def rereserve_pick(self):
        """
        This can be used to provide a button that rereserves taking into account the existing pack operations
        Overridden here to check only moves with available quants in source location.
        """
        for pick in self:
            self.rereserve_quants(pick, move_ids = [m.id for m in pick.move_lines
                                                if m.state not in ('draft','cancel','done') and m.availability > 0.0])
