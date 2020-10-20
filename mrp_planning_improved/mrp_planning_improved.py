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

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession

from openerp import models, fields, api


@job
def run_mrp_recheck_availability(session, model_name, mrp_ids, context):
    mrp_orders = session.env[model_name].with_context(context).browse(mrp_ids)
    mrp_orders.action_assign()
    return "End of assignation"


class ManufacturingOrderPlanningImproved(models.Model):
    _inherit = 'mrp.production'

    date_planned = fields.Datetime(readonly=False,
                                   states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    date_required = fields.Datetime(string="Date required",
                                    states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    taken_into_account = fields.Boolean(string="Taken into account",
                                        help="True if the manufacturing order has been taken into account",
                                        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    final_order_id = fields.Many2one('mrp.production', string="Top parent order",
                                     help="Final parent order in the chain of raw materials and produced products",
                                     compute='_compute_final_order_id')

    @api.multi
    def _compute_final_order_id(self):
        for rec in self:
            production = rec
            move = rec.move_created_ids and rec.move_created_ids[0] or False
            if move:
                while move.move_dest_id:
                    move = move.move_dest_id
                    if not move.move_dest_id and move.raw_material_production_id:
                        production = move.raw_material_production_id
                        move = move.raw_material_production_id.move_created_ids and \
                               move.raw_material_production_id.move_created_ids[0] or False
            rec.final_order_id = production

    @api.multi
    def _get_produce_line_data(self):
        self.ensure_one()
        move_vals = super(ManufacturingOrderPlanningImproved, self)._get_produce_line_data()
        date_move = fields.Datetime.to_string(self.location_dest_id.schedule_working_days(
            self.product_id.produce_delay + 1,
            fields.Datetime.from_string(self.date_planned)
        ))
        move_vals['date_expected'] = date_move
        move_vals['date'] = date_move
        return move_vals

    @api.multi
    def get_date_expected_for_moves(self):
        self.ensure_one()
        days = self.product_id.produce_delay + 1
        format_date_planned = fields.Datetime.from_string(self.date_planned)
        date_expected = self.location_dest_id.schedule_working_days(days, format_date_planned)
        return date_expected

    @api.multi
    def write(self, vals):
        result = super(ManufacturingOrderPlanningImproved, self).write(vals)
        if vals.get('date_planned'):
            for rec in self:
                # Add time if we get only date (e.g. if we have date widget on view)
                if not rec.taken_into_account:
                    date_expected = rec.get_date_expected_for_moves()
                    if date_expected:
                        rec.move_created_ids.write({'date_expected': fields.Datetime.to_string(date_expected)})
        return result

    @api.multi
    def action_reschedule(self):
        for rec in self:
            values = {}
            if rec.taken_into_account:
                if rec.date_required:
                    values['date'] = min(rec.date_planned, rec.date_required)
                else:
                    values['date'] = rec.date_planned
            else:
                values['date'] = rec.date_required or rec.date_planned
            if self.env.context.get('reschedule_planned_date'):
                values['date_expected'] = rec.date_required
            if not values['date']:
                values.pop('date')
            rec.move_lines.write(values)

    @api.model
    def cron_recheck_availibility(self):
        orders = self.search([('state', 'in', ['confirmed', 'in_production'])])
        orders.action_assign()
        chunk_number = 0
        while orders:
            chunk_number += 1
            chunk_orders = orders[:100]
            run_mrp_recheck_availability.delay(ConnectorSession.from_env(self.env), 'mrp.production', chunk_orders.ids,
                                               dict(self.env.context),
                                               description=u"MRP Recheck availability (chunk %s)" % chunk_number)
            orders -= chunk_orders


class ProcurementOrderPlanningImproved(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _prepare_mo_vals(self, procurement):
        result = super(ProcurementOrderPlanningImproved, self)._prepare_mo_vals(procurement)
        result['date_required'] = result.get('date_planned', False)
        return result

    @api.multi
    def action_reschedule(self):
        """Reschedules the moves associated to this procurement."""
        for proc in self:
            if proc.state not in ['done', 'cancel'] and proc.rule_id and proc.rule_id.action == 'manufacture':
                production = proc.production_id
                if production and not self.env.context.get('do_not_propagate_rescheduling'):
                    prod_start_date = self.env['procurement.order']._get_date_planned(proc)
                    prod_end_date = production.location_dest_id.schedule_working_days(
                        -proc.company_id.manufacturing_lead,
                        fields.Datetime.from_string(proc.date_planned)
                    )
                    # Updating the dates of the created moves of the corresponding manufacturing order
                    production.move_created_ids.filtered(lambda move: move.date != prod_end_date). \
                        write({'date': prod_end_date})
                    # Updating the date_required of the corresponding manufacturing order
                    production.date_required = prod_start_date
                    # Updating the date_planned of the corresponding manufacturing order
                    if not production.taken_into_account:
                        # If the production order is not taken into account, then we reschedule date_planned as well
                        production = production.with_context(reschedule_planned_date=True)
                        production.date_planned = prod_start_date
                    production.action_reschedule()
        super(ProcurementOrderPlanningImproved, self).action_reschedule()
