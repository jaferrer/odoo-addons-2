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

from openerp import fields, models, api


class procurement_order_planning_improved(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def action_reschedule(self):
        """Reschedules the moves associated to this procurement."""
        for proc in self:
            if proc.state not in ['done', 'cancel'] and proc.rule_id and proc.rule_id.action == 'move':
                location = proc.location_id or proc.warehouse_id.location_id
                proc_date = fields.Datetime.from_string(proc.date_planned)
                newdate = location.schedule_working_days(-proc.rule_id.delay or 0, proc_date, proc.rule_id.days_of_week)
                vals = {'date': fields.Datetime.to_string(newdate)}
                if self.env.context.get('reschedule_planned_date'):
                    vals.update({'date_expected': fields.Datetime.to_string(newdate)})
                proc.move_ids.write(vals)


class stock_move_planning_improved(models.Model):
    _inherit = 'stock.move'

    date = fields.Datetime(string="Due Date", help="Due date for this stock move to be on schedule.")

    @api.multi
    def onchange_date(self, date, date_expected):
        """Remove link between date and date_expected since they are totally independent."""
        return {}

    @api.model
    def create(self, vals):
        if (not 'date_expected' in vals) and ('date' in vals):
            vals['date_expected'] = vals['date']
        return super(stock_move_planning_improved, self).create(vals)

    @api.multi
    def write(self, vals):
        """Write function overridden to propagate date to previous procurement orders."""
        for move in self:
            if vals.get('date') and vals.get('state') == 'done':
                # If the call is made from action_done, set the date_expected to the done date
                vals['date_expected'] = vals['date']
                # We would have preferred to keep the date to the initial need, but stock calculations are made on date
                # del vals['date']
            if vals.get('date') and move.procure_method == 'make_to_order':
                # If the date is changed and moves are chained, propagate to the previous procurement if any
                proc = self.env['procurement.order'].search([('move_dest_id','=',move.id),
                                                             ('state','not in',['done','cancel'])], limit=1)
                if proc and not self.env.context.get('do_not_propagate_rescheduling'):
                    proc.date_planned = vals.get('date')
                    proc.action_reschedule()
        return super(stock_move_planning_improved, self).write(vals)


class stock_picking_planning_improved(models.Model):
    _inherit = 'stock.picking'

    date_due = fields.Datetime("Due Date", help="Date before which the first moves of this picking must be made so as "
                                                "not to be late on schedule.")

    @api.multi
    def compute_date_due(self):
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

    @api.model
    def compute_date_due_auto(self):
        pickings = self.search([('state', 'not in', ['cancel', 'done'])])
        pickings.compute_date_due()
