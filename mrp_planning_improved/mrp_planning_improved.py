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

from openerp import models, fields, api
from datetime import timedelta


class ManufacturingOrderPlanningImproved(models.Model):
    _inherit = 'mrp.production'

    date_planned = fields.Datetime(readonly=False,
                                   states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    date_required = fields.Datetime(string="Date required",
                                    states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    taken_into_account = fields.Boolean(string="Taken into account",
                                        help="True if the manufacturing order has been taken into account",
                                        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    procurement_id = fields.Many2one('procurement.order', string="Corresponding procurement order",
                                     compute='_compute_procurement_id', readonly=True)

    @api.multi
    def _compute_procurement_id(self):
        for rec in self:
            list_procurements = self.env['procurement.order'].search([('production_id', '=', rec.id)])
            if list_procurements and len(list_procurements) == 1:
                rec.procurement_id = list_procurements[0]

    @api.multi
    def write(self, vals):
        result = super(ManufacturingOrderPlanningImproved, self).write(vals)
        if vals.get('date_planned'):
            for rec in self:
                for move in rec.move_created_ids:
                    move.date_expected = vals['date_planned']
        return result

    @api.multi
    def action_reschedule(self):
        for rec in self:
            if rec.taken_into_account:
                rec.move_lines.write({'date': min(rec.date_planned, rec.date_required)})
            else:
                rec.move_lines.write({'date': rec.date_required})
            if self.env.context.get('reschedule_planned_date'):
                rec.move_lines.write({'date_expected': rec.date_required})


class ProcurementOrderPlanningImproved(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _prepare_mo_vals(self, procurement):
        result = super(ProcurementOrderPlanningImproved, self)._prepare_mo_vals(procurement)
        if result.get('date_planned'):
            result['date_required'] = result['date_planned']
        return result

    @api.multi
    def action_reschedule(self):
        """Reschedules the moves associated to this procurement."""
        for proc in self:
            if proc.state not in ['done', 'cancel'] and proc.rule_id and proc.rule_id.action == 'manufacture':
                if proc.production_id:
                    # Updating the dates of the created moves of the corresponding manufacturing order
                    if proc.production_id.move_created_ids:
                        for move in proc.production_id.move_created_ids:
                            if move.date != proc.date_planned:
                                move.date = proc.date_planned
                    # Updating the date_required of the corresponding manufacturing order
                    proc.production_id.date_required = fields.Datetime.from_string(proc.date_planned)\
                                                                       - timedelta(proc.company_id.manufacturing_lead)
                    # Updating the date_planned of the corresponding manufacturing order
                    if self.env.context.get('reschedule_planned_date') and not proc.production_id.taken_into_account:
                        if proc.production_id.date_planned != fields.Datetime.from_string(proc.date_planned)\
                                                                       - timedelta(proc.company_id.manufacturing_lead):
                            proc.production_id.date_planned = fields.Datetime.from_string(proc.date_planned)\
                                                               - timedelta(proc.company_id.manufacturing_lead)
        super(ProcurementOrderPlanningImproved, self).action_reschedule()