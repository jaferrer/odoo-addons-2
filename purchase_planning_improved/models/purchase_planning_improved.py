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

import openerp.addons.decimal_precision as dp
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import job

from openerp import modules, fields, models, api, osv, _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, float_round


@job(default_channel='root.compute_coverage_state')
def job_compute_coverage_state(session, model_name, pol_id, context):
    pol_id = session.env[model_name].browse(pol_id)
    if pol_id:
        pol_id.with_context(context).compute_coverage_state()
        return u"The coverage state of line no %s (%s) is recomputed" % (pol_id.line_no, pol_id.order_id.name)
    else:
        return u"Purchase order line not found for id %i" % pol_id


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
    def _get_remaining_qty(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            remaining_qty = 0
            if line.product_id and line.product_id.type != 'service':
                delivered_qty = sum([self.pool.get('product.uom').
                                    _compute_qty(cr, uid, move.product_uom.id,
                                                 move.product_uom_qty, line.product_uom.id)
                                     for move in line.move_ids if move.state == 'done'])
                remaining_qty = float_round(line.product_qty - delivered_qty,
                                            precision_rounding=line.product_uom.rounding)
            res[line.id] = remaining_qty
            if res[line.id] == line.remaining_qty:
                del res[line.id]
        return res

    @api.cr_uid_ids_context
    def _get_purchase_order_lines(self, cr, uid, ids, context=None):
        res = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.purchase_line_id:
                res.add(move.purchase_line_id.id)
        return list(res)

    confirm_date = fields.Datetime(string=u"Confirm date", readonly=True)
    date_required = fields.Date(string=u"Required Date", help=u"Required date for this purchase line. "
                                                              u"Computed as planned date of the first proc - supplier purchase "
                                                              u"lead time - company purchase lead time", readonly=True)
    limit_order_date = fields.Date(string=u"Limit Order Date", help=u"Limit order date to be late :required date - "
                                                                    u"supplier delay", readonly=True)
    covering_date = fields.Date(string=u"Covered Date", readonly=True)
    covering_state = fields.Selection([
        ('all_covered', u"All Need Covered"),
        ('coverage_computed', u"Computed Coverage"),
        ('unknown_coverage', u"Not Calculated State")
    ], string=u"Covered State", default='unknown_coverage', required=True, readonly=True)
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
    to_delete = fields.Boolean(u"True if all the needs corresponding to the purchase order line are cancelled")
    opmsg_reduce_qty = fields.Float(string=u"New target quantity", readonly=True, default=False)
    opmsg_type = fields.Selection([('no_msg', "Ok"), ('late', "LATE"), ('early', "EARLY"), ('reduce', "REDUCE"),
                                   ('to_cancel', "CANCEL")], compute='_compute_opmsg', string=u"Message Type")
    opmsg_delay = fields.Integer(string=u"Message Delay", compute='_compute_opmsg')
    opmsg_text = fields.Char(string=u"Operational message", compute='_compute_opmsg_text',
                             help=u"This field holds the operational messages generated by the system to the operator")

    _columns = {
        'remaining_qty': osv.fields.function(
            _get_remaining_qty, type="float", copy=False, digits_compute=dp.get_precision('Product Unit of Measure'),
            store={
                'purchase.order.line': (lambda self, cr, uid, ids, ctx: ids, ['product_qty'], 20),
                'stock.move': (_get_purchase_order_lines, ['purchase_line_id', 'product_uom_qty',
                                                           'product_uom', 'state'], 20)},
            string="Remaining quantity", help="Quantity not yet delivered by the supplier")}

    @api.depends('date_planned', 'date_required', 'to_delete', 'product_qty', 'opmsg_reduce_qty')
    def _compute_opmsg(self):
        """
        Sets parameters date_planned, date_required, and opmsg_type.
        """

        for rec in self:
            if rec.date_planned and rec.date_required:
                date_planned = datetime.strptime(rec.date_planned, DEFAULT_SERVER_DATE_FORMAT)
                date_required = datetime.strptime(rec.date_required, DEFAULT_SERVER_DATE_FORMAT)
                min_late_days = int(self.env['ir.config_parameter'].
                                    get_param('purchase_planning_improved.opmsg_min_late_delay'))
                min_early_days = int(self.env['ir.config_parameter'].
                                     get_param('purchase_planning_improved.opmsg_min_early_delay'))
                if date_planned >= date_required:
                    delta = date_planned - date_required
                    if delta.days >= min_late_days:
                        rec.opmsg_type = 'late'
                        rec.opmsg_delay = delta.days
                else:
                    delta = date_required - date_planned
                    if delta.days >= min_early_days:
                        rec.opmsg_type = 'early'
                        rec.opmsg_delay = delta.days
            if rec.to_delete and rec.product_qty != 0:
                rec.opmsg_type = 'to_cancel'
            if not rec.to_delete and rec.opmsg_reduce_qty and rec.opmsg_reduce_qty < rec.product_qty:
                rec.opmsg_type = 'reduce'

    @api.depends('opmsg_type', 'opmsg_delay', 'opmsg_reduce_qty', 'product_qty', 'to_delete', 'state')
    def _compute_opmsg_text(self):
        """
        Sets parameters opmsg_type, opmsg_delay, opmsg_reduce_qty, product_qty, to_delete and state.
        """

        for rec in self:
            msg = ""
            if rec.to_delete and rec.product_qty != 0:
                msg += _(u"CANCEL LINE")
            if not rec.to_delete and rec.opmsg_reduce_qty and rec.opmsg_reduce_qty < rec.product_qty:
                msg += _(u"REDUCE QTY to %.1f %s") % (rec.opmsg_reduce_qty, rec.product_uom.name)
            if rec.opmsg_type == 'early':
                msg += _(u"EARLY by %i day(s)") % rec.opmsg_delay
            elif rec.opmsg_type == 'late':
                msg += _(u"LATE by %i day(s)") % rec.opmsg_delay
            rec.opmsg_text = msg

    @api.multi
    def compute_coverage_state(self):
        module_path = modules.get_module_path('purchase_planning_improved')
        products = self.mapped('product_id')
        if not products:
            return
        with open(module_path + '/sql/' + 'covering_dates_query.sql') as sql_file:
            self.env.cr.execute(sql_file.read(), (tuple(products.ids),))
            for result_line in self.env.cr.dictfetchall():
                line = self.env['purchase.order.line'].search([('id', '=', result_line['pol_id'])])
                if line.product_id.type == 'product':
                    real_need_date = result_line['real_need_date'] or False
                    date_required = real_need_date and self.env['procurement.order']. \
                        _get_purchase_schedule_date(procurement=False,
                                                    company=line.order_id.company_id,
                                                    ref_product=line.product_id,
                                                    ref_location=line.order_id.location_id,
                                                    ref_date=real_need_date) or False
                    limit_order_date = date_required and self.env['procurement.order']. \
                        with_context(force_partner_id=line.order_id.partner_id.id). \
                        _get_purchase_order_date(procurement=False,
                                                 company=line.order_id.company_id,
                                                 schedule_date=date_required,
                                                 ref_product=line.product_id) or False
                    limit_order_date = limit_order_date and fields.Datetime.to_string(limit_order_date) or False
                    date_required = date_required and fields.Datetime.to_string(date_required) or False
                    dict_pol = {
                        'date_required': date_required,
                        'limit_order_date': limit_order_date,
                        'covering_date': result_line['covering_date'] or False,
                        'covering_state': result_line['covering_date'] and 'coverage_computed' or 'all_covered',
                        'to_delete': result_line['to_delete'],
                        'opmsg_reduce_qty': result_line['opmsg_reduce_qty'] or 0,
                    }
                else:
                    dict_pol = {
                        'date_required': False,
                        'limit_order_date': False,
                        'covering_date': False,
                        'covering_state': 'unknown_coverage',
                        'to_delete': False,
                        'opmsg_reduce_qty': line.product_qty,
                    }
                line.write(dict_pol)

    @api.model
    def cron_compute_coverage_state(self):
        pol_coverage_to_recompute = self.search([('order_id.state', '!=', 'draft'), ('remaining_qty', '>', 0)])
        for pol in pol_coverage_to_recompute:
            job_compute_coverage_state.delay(ConnectorSession.from_env(self.env), 'purchase.order.line', pol.id,
                                             context=dict(self.env.context),
                                             description=u"Update coverage state for line no %s (%s)" % (
                                             pol.line_no, pol.order_id.name))

    @api.multi
    def set_moves_dates(self, date_required):
        for rec in self:
            moves = rec.move_ids.filtered(lambda m: m.state not in ['draft', 'cancel'])
            moves.filtered(lambda move: move.date != date_required).write({'date': date_required})

    @api.model
    def create(self, vals):
        if vals.get('date_planned'):
            vals['requested_date'] = vals['date_planned']
        result = super(PurchaseOrderLinePlanningImproved, self).create(vals)
        result.compute_coverage_state()
        return result

    @api.multi
    def write(self, vals):
        """write method overridden here to propagate date_planned to the stock_moves of the receipt."""
        need_cover_reset = 'product_qty' in vals or 'product_uom' in vals or 'order_id' in vals or 'product_id' in vals
        if need_cover_reset:
            vals['covering_state'] = 'unknown_coverage'
            vals['covering_date'] = False
        if 'date_planned' in vals:
            for line in self:
                if vals.get('stats', line.state) == 'draft':
                    vals['requested_date'] = vals['date_planned']
        result = super(PurchaseOrderLinePlanningImproved, self).write(vals)
        if 'date_planned' in vals:
            date = vals.get('date_planned') + " 12:00:00"
            for line in self:
                moves = self.env['stock.move'].search([('purchase_line_id', '=', line.id),
                                                       ('state', 'not in', ['done', 'cancel'])])
                if line.procurement_ids:
                    moves.write({'date_expected': date})
                else:
                    moves.write({'date_expected': date, 'date': date})
        if need_cover_reset:
            self.compute_coverage_state()
        return result


class PurchaseOrderPlanningImproved(models.Model):
    _inherit = 'purchase.order'

    confirm_date = fields.Datetime(string=u"Confirm date", readonly=True)
    limit_order_date = fields.Date(string=u"Limit order date to be late", readonly=True)

    @api.model
    def cron_compute_limit_order_date(self):
        self.env.cr.execute("""SELECT
  po.id                     AS order_id,
  min(pol.limit_order_date) AS new_limit_order_date
FROM purchase_order po
  INNER JOIN purchase_order_line pol ON pol.order_id = po.id AND pol.limit_order_date IS NOT NULL
GROUP BY po.id
ORDER BY po.id""")
        result = self.env.cr.dictfetchall()
        order_with_limit_dates_ids = []
        for item in result:
            order = self.search([('id', '=', item['order_id'])])
            if order.limit_order_date != item['new_limit_order_date']:
                order.limit_order_date = item['new_limit_order_date']
            order_with_limit_dates_ids += [item['order_id']]
        self.search([('id', 'not in', order_with_limit_dates_ids)]).write({'limit_order_date': False})

    @api.multi
    def compute_coverage_state(self):
        self.mapped('order_line').compute_coverage_state()

    @api.multi
    def write(self, vals):
        """write method overridden here to propagate date_planned to the stock_moves of the receipt."""
        if vals.get('state') == 'approved':
            date_now = fields.Datetime.now()
            vals['confirm_date'] = date_now
            order_lines = self.env['purchase.order.line'].search([('order_id', 'in', self.ids)])
            if order_lines:
                order_lines.write({'confirm_date': date_now})
        if vals.get('state') in ['draft', 'cancel']:
            vals['confirm_date'] = False
            order_lines = self.env['purchase.order.line'].search([('order_id', 'in', self.ids)])
            if order_lines:
                order_lines.write({'confirm_date': False})
        return super(PurchaseOrderPlanningImproved, self).write(vals)
