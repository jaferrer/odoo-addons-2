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
from openerp.osv import fields as old_api_fields


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

    @api.cr_uid_ids_context
    def _compute_dates(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            partner = line.order_id.partner_id
            line_data = {'date_required': line.date_required, 'limit_order_date': line.limit_order_date}
            if line.procurement_ids:
                min_date = min([p.date_planned for p in line.procurement_ids])
                min_proc = line.procurement_ids.filtered(lambda proc: str(proc.date_planned) == min_date)[0]
                if min_proc.rule_id:
                    context = dict(context, do_not_save_result=True, force_partner_id=partner.id)
                    date_required = self.pool.get('procurement.order'). \
                        _get_purchase_schedule_date(cr, uid, min_proc, line.company_id, context=context)
                    limit_order_date = self.pool.get('procurement.order'). \
                        _get_purchase_order_date(cr, uid, min_proc, line.company_id, date_required, context=context)
                    limit_order_date = limit_order_date and fields.Datetime.to_string(limit_order_date) or False
                    date_required = date_required and fields.Datetime.to_string(date_required) or False
                else:
                    date_required = min_date
                    limit_order_date = min_date
            else:
                date_required = line.date_planned
                limit_order_date = line.date_planned
            target_data = {'date_required': date_required and date_required[:10] or False,
                           'limit_order_date': limit_order_date and limit_order_date[:10] or False}
            if target_data != line_data:
                res[line.id] = target_data
        return res

    @api.cr_uid_ids_context
    def _get_order_lines(self, cr, uid, ids, context=None):
        res = set()
        for line in self.browse(cr, uid, ids, context=context):
            if line.purchase_line_id:
                res.add(line.purchase_line_id.id)
        return list(res)

    _columns = {
        'date_required': old_api_fields.function(_compute_dates, type='date', string=u"Required Date",
                                                 help=u"Required date for this purchase line. "
                                                      "Computed as planned date of the first proc - supplier purchase "
                                                      "lead time - company purchase lead time",
                                                 multi="compute_dates",
                                                 store={
                                                     'purchase.order.line': (lambda self, cr, uid, ids, ctx: ids,
                                                                             ['date_planned'], 20),
                                                     'procurement.order': (_get_order_lines,
                                                                           ['date_planned', 'purchase_line_id'], 20)
                                                 }, readonly=True),
        'limit_order_date': old_api_fields.function(_compute_dates, type='date', string=u"Limit Order Date",
                                                    help=u"Limit order date to be late : required date - supplier delay",
                                                    multi="compute_dates",
                                                    store={
                                                        'purchase.order.line': (lambda self, cr, uid, ids, ctx: ids,
                                                                                ['order_id', 'date_planned'], 20),
                                                        'procurement.order': (_get_order_lines,
                                                                              ['date_planned', 'purchase_line_id'], 20)
                                                    }, readonly=True),
    }

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

    @api.cr_uid_ids_context
    def _compute_limit_order_date(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            first_line_id = self.pool.get('purchase.order.line'). \
                search(cr, uid, [('order_id', '=', order.id)], order='limit_order_date', limit=1, context=context)
            first_line = self.pool.get('purchase.order.line').browse(cr, uid, first_line_id, context=context)
            limit_order_date = first_line and first_line.limit_order_date or False
            if limit_order_date != order.limit_order_date:
                res[order.id] = limit_order_date
        return res

    @api.cr_uid_ids_context
    def _get_orders(self, cr, uid, ids, context=None):
        res = set()
        for line in self.browse(cr, uid, ids, context=context):
            if line.order_id:
                res.add(line.order_id.id)
        return list(res)

    _columns = {
        'limit_order_date': old_api_fields.function(_compute_limit_order_date, type='date', string=u"Limit Order Date",
                                                    help=u"Minimum of limit order dates of all the lines",
                                                    store={
                                                        'procurement.order.line': (_get_orders,
                                                                                   ['order_id', 'limit_order_date'], 20)
                                                    }, readonly=True),
    }

    @api.multi
    def write(self, vals):
        """write method overridden here to propagate date_planned to the stock_moves of the receipt."""
        result = super(PurchaseOrderPlanningImproved, self).write(vals)
        if vals.get('state') == 'approved':
            order_lines = self.env['purchase.order.line'].search([('order_id', 'in', self.ids)])
            if order_lines:
                order_lines.write({'confirm_date': fields.Datetime.now()})
        return result
