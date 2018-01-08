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

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp import fields, models, api


class ProcurementOrderPurchasePlanningImproved(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def action_reschedule(self):
        """Reschedules the moves associated to this procurement."""
        for proc in self:
            if proc.state not in ['done', 'cancel', 'exception'] and proc.rule_id and proc.rule_id.action == 'buy' and \
                    not self.env.context.get('do_not_propagate_rescheduling'):
                schedule_date = self._get_purchase_schedule_date(proc, proc.company_id)
                order_date = self._get_purchase_order_date(proc, proc.company_id, schedule_date)
                # We sudo because the user has not necessarily the rights to update PO and PO lines
                proc = proc.sudo()
                # If the purchase line is not confirmed yet, try to set planned date to schedule_date
                if proc.purchase_id.state in ['sent', 'bid'] and order_date > datetime.now() and not \
                        self.env.context.get('do_not_reschedule_bigd_and_sent') or proc.purchase_id.state == 'draft':
                    proc.purchase_line_id.date_planned = fields.Date.to_string(schedule_date)
                if proc.purchase_id and fields.Datetime.from_string(proc.purchase_id.date_order) > order_date and not \
                        self.env.context.get('do_not_move_purchase_order'):
                    proc.purchase_id.date_order = fields.Datetime.to_string(order_date)
                proc.purchase_line_id.set_moves_dates(proc.purchase_line_id.date_required)
        return super(ProcurementOrderPurchasePlanningImproved, self).action_reschedule()

    @api.model
    def _get_po_line_values_from_proc(self, procurement, partner, company, schedule_date):
        """Overridden to set date_required."""
        res = super(ProcurementOrderPurchasePlanningImproved, self)._get_po_line_values_from_proc(
            procurement, partner, company, schedule_date)
        res.update({
            'requested_date': schedule_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
        })
        return res


class PurchaseOrderLinePlanningImproved(models.Model):
    _inherit = 'purchase.order.line'

    date_required = fields.Date("Required Date", compute="_compute_dates", store=True,
                                help="Required date for this purchase line. Computed as planned date of the first proc "
                                     "- supplier purchase lead time - company purchase lead time")
    limit_order_date = fields.Date("Limit Order Date", compute="_compute_dates", store=True,
                                   help="Limit order date to be late : required date - supplier delay")
    confirm_date = fields.Datetime("Confirm date", help="Confirmation Date", readonly=True)
    requested_date = fields.Date("Requested date", help="The line was required to the supplier at that date",
                                 default=fields.Date.context_today, states={'sent': [('readonly', True)],
                                                                            'bid': [('readonly', True)],
                                                                            'confirmed': [('readonly', True)],
                                                                            'approved': [('readonly', True)],
                                                                            'except_picking': [('readonly', True)],
                                                                            'except_invoice': [('readonly', True)],
                                                                            'done': [('readonly', True)],
                                                                            'cancel': [('readonly', True)],
                                                                            })

    @api.multi
    def set_moves_dates(self, date_required):
        for rec in self:
            moves = rec.move_ids.filtered(lambda m: m.state not in ['draft', 'cancel'])
            moves.filtered(lambda move: move.date != date_required).write({'date': date_required})

    @api.multi
    @api.depends('procurement_ids', 'procurement_ids.date_planned', 'date_planned')
    def _compute_dates(self):
        for rec in self:
            if rec.procurement_ids:
                min_date = min([p.date_planned for p in rec.procurement_ids])
                min_proc = rec.procurement_ids.filtered(lambda proc: str(proc.date_planned) == min_date)[0]
                if min_proc.rule_id:
                    date_required = self.env['procurement.order'].with_context(do_not_save_result=True). \
                        _get_purchase_schedule_date(min_proc, rec.company_id)
                    limit_order_date = self.env['procurement.order']._get_purchase_order_date(min_proc, rec.company_id,
                                                                                              date_required)
                    limit_order_date = limit_order_date and fields.Datetime.to_string(limit_order_date) or False
                    date_required = date_required and fields.Datetime.to_string(date_required) or False
                else:
                    date_required = min_date
                    limit_order_date = min_date
            else:
                date_required = rec.date_planned
                limit_order_date = rec.date_planned
            rec.date_required = date_required and date_required[:10] or False
            rec.limit_order_date = limit_order_date and limit_order_date[:10] or False

    @api.model
    def create(self, vals):
        if vals.get('date_planned'):
            vals['requested_date'] = vals['date_planned']
        return super(PurchaseOrderLinePlanningImproved, self).create(vals)

    @api.multi
    def write(self, vals):
        """write method overridden here to propagate date_planned to the stock_moves of the receipt."""
        if vals.get('date_planned'):
            for line in self:
                if line.state == "draft" and vals.get('status', 'draft') == 'draft':
                    vals['requested_date'] = vals['date_planned']
        result = super(PurchaseOrderLinePlanningImproved, self).write(vals)
        if vals.get('date_planned'):
            date = vals.get('date_planned') + " 12:00:00"
            for line in self:
                moves = self.env['stock.move'].search([('purchase_line_id', '=', line.id),
                                                       ('state', 'not in', ['done', 'cancel'])])
                if line.procurement_ids:
                    moves.write({'date_expected': date})
                else:
                    moves.write({'date_expected': date, 'date': date})
        return result


class PurchaseOrderPlanningImproved(models.Model):
    _inherit = 'purchase.order'

    limit_order_date = fields.Date("Limit order date", compute="_compute_limit_order_date",
                                   help="Minimum of limit order dates of all the lines")

    @api.multi
    @api.depends('order_line', 'order_line.limit_order_date')
    def _compute_limit_order_date(self):
        for rec in self:
            rec.limit_order_date = min([line.limit_order_date for line in rec.order_line])

    @api.multi
    def write(self, vals):
        """write method overridden here to propagate date_planned to the stock_moves of the receipt."""
        result = super(PurchaseOrderPlanningImproved, self).write(vals)
        if vals.get('state') == 'approved':
            order_lines = self.env['purchase.order.line'].search([('order_id', 'in', self.ids)])
            if order_lines:
                order_lines.write({'confirm_date': fields.Datetime.now()})
        return result
