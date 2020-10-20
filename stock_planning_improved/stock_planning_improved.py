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

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession

from openerp import fields, models, api, _


@job
def job_compute_date_due(session, model_name, data, context):
    session.env[model_name].with_context(context).compute_date_due(data)
    return "End update"


class ProcurementOrderPlanningImproved(models.Model):
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
                # We do not write in moves which dest loc is not the same as the procurement's location
                # (ex: return moves, which are linked to the same procurements as the original ones)
                proc.move_ids.filtered(lambda move: (move.location_dest_id == proc.location_id and
                                                     (move.date != vals['date'] or
                                                      vals.get('date_expected') and
                                                      move.date_expected != vals['date_expected']))).write(vals)


class StockMovePlanningImproved(models.Model):
    _inherit = 'stock.move'

    date = fields.Datetime(string="Due Date", help="Due date for this stock move to be on schedule.")
    transferred_by_id = fields.Many2one('res.users', string=u'Transferred by', readonly=True)

    @api.multi
    def onchange_date(self, date, date_expected):
        """Remove link between date and date_expected since they are totally independent."""
        return {}

    @api.model
    def create(self, vals):
        if not ('date_expected' in vals) and ('date' in vals):
            vals['date_expected'] = vals['date']
        return super(StockMovePlanningImproved, self).create(vals)

    @api.multi
    def write(self, vals):
        """Write function overridden to propagate date to previous procurement orders
        and assign user who has transferred the move"""
        if vals.get('date') and vals.get('state') == 'done':
            # If the call is made from action_done, set the date_expected to the done date
            vals['date_expected'] = vals['date']
            # We would have preferred to keep the date to the initial need, but stock calculations are made on date
            # del vals['date']
        for move in self:
            if vals.get('date') and vals.get('state') != 'done' and move.procure_method == 'make_to_order':
                # If the date is changed and moves are chained, propagate to the previous procurement if any
                proc = self.env['procurement.order'].search([('move_dest_id', '=', move.id),
                                                             ('state', 'not in', ['done', 'cancel'])], limit=1)
                if proc and not self.env.context.get('do_not_propagate_rescheduling'):
                    proc.date_planned = vals.get('date')
                    proc.action_reschedule()

        if vals.get('state') and vals['state'] == 'done':
            vals['transferred_by_id'] = self.env.user.id

        return super(StockMovePlanningImproved, self).write(vals)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        new_order = ", ".join(orderby and groupby + [orderby] or groupby)
        return super(StockMovePlanningImproved, self).read_group(
            domain, fields, groupby, offset, limit=limit, context=self.env.context, orderby=new_order, lazy=lazy)


class StockPickingPlanningImproved(models.Model):
    _inherit = 'stock.picking'

    date_due = fields.Datetime("Due Date", help="Date before which the first moves of this picking must be made so as "
                                                "not to be late on schedule.")

    @api.model
    def compute_date_due(self, data):
        if not data:
            return
        for item in data:
            self.browse(item['picking_id']).date_due = item['date_due'] or False

    @api.model
    def compute_date_due_auto(self):
        self.env.cr.execute("""SELECT sp.id        AS picking_id,
       min(sm.date) AS date_due
FROM stock_move sm
       INNER JOIN stock_picking sp ON sp.id = sm.picking_id
WHERE sp.state NOT IN ('cancel', 'done')
GROUP BY sp.id
HAVING sp.date_due IS NULL
    OR sp.date_due::DATE != MIN(sm.date)::DATE""")
        result = self.env.cr.dictfetchall()
        while result:
            chunk_result = result[:100]
            job_compute_date_due.delay(ConnectorSession.from_env(self.env), 'stock.picking', chunk_result,
                                       dict(self.env.context))
            result = result[100:]


class OpenGroupedMoves(models.TransientModel):
    _name = 'open.grouped.moves'

    def _get_default_date_end(self):
        return fields.Datetime.now()

    date_begin = fields.Date(string=u"Date begin")
    date_end = fields.Date(string=u"Date end", default=_get_default_date_end)
    user_ids = fields.Many2many('res.users', string=u"User(s)")
    only_done_moves = fields.Boolean(string=u"Focus on done moves", default=True)

    @api.multi
    def open_grouped_moves(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        moves_domain = [('state', '!=', 'cancel')]
        if self.date_begin:
            moves_domain += [('date', '>=', self.date_begin)]
        if self.date_end:
            moves_domain += [('date', '<=', self.date_end)]
        if self.user_ids:
            moves_domain += [('transferred_by_id', 'in', self.user_ids.ids)]
        if self.only_done_moves:
            ctx['search_default_done'] = True
        ctx['search_default_groupby_date_real'] = True
        ctx['search_default_groupby_user'] = True
        return {
            'name': _("Grouped moves by users"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.move',
            'domain': moves_domain,
            'context': ctx,
        }
