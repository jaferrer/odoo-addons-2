# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from datetime import datetime as dt

from dateutil.relativedelta import relativedelta
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession, ConnectorSessionHandler

from openerp import models, fields, api, _
from openerp.tools.float_utils import float_compare, float_round


@job(default_channel='root.purchase_scheduler')
def job_purchase_schedule(session, model_name, compute_all_products, compute_supplier_ids,
                          compute_product_ids, jobify):
    result = session.env[model_name].launch_purchase_schedule(compute_all_products,
                                                              compute_supplier_ids,
                                                              compute_product_ids,
                                                              jobify)
    return result


@job(default_channel='root.purchase_scheduler')
def job_purchase_schedule_procurements(session, model_name, ids):
    result = session.env[model_name].browse(ids).purchase_schedule_procurements(jobify=True)
    return result


@job(default_channel='root.purchase_scheduler_slave')
def job_create_draft_lines(session, model_name, dict_lines_to_create):
    result = session.env[model_name].create_draft_lines(dict_lines_to_create)
    return result


@job(default_channel='root.purchase_scheduler_slave')
def job_redistribute_procurements_in_lines(session, model_name, dict_procs_lines):
    result = session.env[model_name].redistribute_procurements_in_lines(dict_procs_lines)
    return result


class ProductSupplierinfoJIT(models.Model):
    _inherit = 'product.supplierinfo'
    _order = 'sequence, id'


class ProcurementOrderPurchaseJustInTime(models.Model):
    _inherit = 'procurement.order'

    state = fields.Selection([('cancel', "Cancelled"),
                              ('confirmed', "Confirmed"),
                              ('exception', "Exception"),
                              ('buy_to_run', "Buy rule to run"),
                              ('running', "Running"),
                              ('done', "Done")])

    @api.model
    def propagate_cancel(self, procurement):
        """
        Improves the original propagate_cancel function. If the corresponding purchase order is draft, it eventually
        cancels and/or deletes the purchase order line and the purchase order.
        """
        result = None
        if procurement.rule_id.action == 'buy' and procurement.purchase_line_id:
            # Keep proc with new qty if some moves are already done
            procurement.remove_done_moves()
        else:
            result = super(ProcurementOrderPurchaseJustInTime, self).propagate_cancel(procurement)
        return result

    @api.model
    def _get_product_supplier(self, procurement):
        ''' returns the main supplier of the procurement's product given as argument'''
        company_supplier = procurement.product_id.product_tmpl_id. \
            get_main_supplierinfo(force_company=procurement.company_id)
        if company_supplier:
            return company_supplier.name
        return procurement.product_id.seller_id

    @api.model
    def remove_done_moves(self):
        """Splits the given procs creating a copy with the qty of their done moves and set to done.
        """
        for procurement in self:
            if procurement.rule_id.action == 'buy':
                qty_done_product_uom = sum([m.product_qty for m in procurement.move_ids if m.state == 'done'])
                qty_done_proc_uom = self.env['product.uom']._compute_qty(procurement.product_id.uom_id.id,
                                                                         qty_done_product_uom,
                                                                         procurement.product_uom.id)
                remaining_qty = procurement.product_qty - qty_done_proc_uom
                prec = procurement.product_uom.rounding
                if float_compare(qty_done_proc_uom, 0.0, precision_rounding=prec) > 0 and \
                                float_compare(remaining_qty, 0.0, precision_rounding=prec) > 0:
                    new_proc = procurement.copy({
                        'product_qty': float_round(qty_done_proc_uom,
                                                   precision_rounding=procurement.product_uom.rounding),
                        'state': 'done',
                    })
                    procurement.write({
                        'product_qty': float_round(remaining_qty,
                                                   precision_rounding=procurement.product_uom.rounding),
                    })
                    # Attach done and cancelled moves to new_proc
                    done_moves = procurement.move_ids.filtered(lambda m: m.state in ['done', 'cancel'])
                    done_moves.write({'procurement_id': new_proc.id})
                # Detach the other moves and reconfirm them so that we have push rules applied if any
                remaining_moves = procurement.move_ids.filtered(lambda m: m.state not in ['done', 'cancel'])
                remaining_moves.write({
                    'procurement_id': False,
                    'move_dest_id': False,
                })
                remaining_moves.action_confirm()
                remaining_moves.force_assign()
        return super(ProcurementOrderPurchaseJustInTime, self).remove_done_moves()

    @api.model
    def purchase_schedule(self, compute_all_products=True, compute_supplier_ids=None, compute_product_ids=None,
                          jobify=True):
        compute_supplier_ids = compute_supplier_ids and compute_supplier_ids.ids or []
        compute_product_ids = compute_product_ids and compute_product_ids.ids or []
        if jobify:
            session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
            job_purchase_schedule.delay(session, 'procurement.order', compute_all_products,
                                        compute_supplier_ids, compute_product_ids, jobify,
                                        description=_("Scheduling purchase orders"))
        else:
            self.launch_purchase_schedule(compute_all_products, compute_supplier_ids, compute_product_ids, jobify)

    @api.model
    def launch_purchase_schedule(self, compute_all_products, compute_supplier_ids, compute_product_ids, jobify):
        self.env['product.template'].update_seller_ids()
        domain_procurements_to_run = [('state', 'not in', ['cancel', 'done', 'exception']),
                                      ('rule_id.action', '=', 'buy')]
        if not compute_all_products and compute_product_ids:
            domain_procurements_to_run += [('product_id', 'in', compute_product_ids)]
        procurements_to_run = self.search(domain_procurements_to_run)
        ignore_past_procurements = bool(self.env['ir.config_parameter'].
                                        get_param('purchase_procurement_just_in_time.ignore_past_procurements'))
        # dict_procs groups procurements by supplier, company and location, in order to
        # launch the purchase planner on each group
        dict_procs = {}
        while procurements_to_run:
            seller = self.env['procurement.order']._get_product_supplier(procurements_to_run[0])
            if not seller:
                # If the first proc has no seller, then we drop this proc and go to the next
                procurements_to_run = procurements_to_run[1:]
                procurements_to_run.set_exception_no_supplier()
                continue
            seller_ok = bool(compute_all_products or not compute_supplier_ids or
                             compute_supplier_ids and seller.id in compute_supplier_ids)
            company = procurements_to_run[0].company_id
            product = procurements_to_run[0].product_id
            location = procurements_to_run[0].location_id
            domain = [('id', 'in', procurements_to_run.ids),
                      ('company_id', '=', company.id),
                      ('product_id', '=', product.id),
                      ('location_id', '=', location.id)]
            if seller_ok and ignore_past_procurements:
                suppliers = product.seller_ids and self.env['product.supplierinfo']. \
                    search([('id', 'in', product.seller_ids.ids),
                            ('name', '=', seller.id)]) or False
                if suppliers:
                    min_date = fields.Datetime.to_string(
                        seller.schedule_working_days(product.seller_delay, dt.now()))
                else:
                    min_date = fields.Datetime.now()
                past_procurements = self.search(domain + [('date_planned', '<=', min_date)])
                if past_procurements:
                    procurements_to_run -= past_procurements
                    past_procurements.remove_procs_from_lines(unlink_moves_to_procs=True)
                domain += [('date_planned', '>', min_date)]
            procurements = self.search(domain)
            if seller_ok and procurements:
                if not dict_procs.get(seller):
                    dict_procs[seller] = {}
                if not dict_procs[seller].get(company):
                    dict_procs[seller][company] = {}
                if not dict_procs[seller][company].get(location):
                    dict_procs[seller][company][location] = procurements
                else:
                    dict_procs[seller][company][location] += procurements
            procurements_to_run -= procurements
        for supplier in sorted(dict_procs.keys(), key=lambda partner: partner.scheduler_sequence):
            for company in dict_procs[supplier].keys():
                for location in dict_procs[supplier][company].keys():
                    procurements = dict_procs[supplier][company][location]
                    if procurements:
                        if jobify:
                            session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
                            job_purchase_schedule_procurements. \
                                delay(session, 'procurement.order', procurements.ids,
                                      description=_("Scheduling purchase orders for seller %s, "
                                                    "company %s and location %s") %
                                                  (supplier.display_name, company.display_name, location.display_name))
                        else:
                            procurements.purchase_schedule_procurements()

    @api.multi
    def compute_procs_for_first_line_found(self, purchase_lines, dict_procs_lines):
        pol = purchase_lines[0]
        procs_for_first_line = self.env['procurement.order'].search([('purchase_line_id', '=', pol.id),
                                                                     ('state', 'in', ['done', 'cancel'])])
        remaining_qty = pol.remaining_qty
        procurements = self
        for proc in procurements:
            remaining_proc_qty_pol_uom = self.env['product.uom']. \
                                             _compute_qty(proc.product_uom.id, proc.product_qty, pol.product_uom.id) - \
                                         self.env['product.uom']. \
                                             _compute_qty(proc.product_id.uom_id.id,
                                                          sum([move.product_qty for move in proc.move_ids
                                                               if move.state == 'done']),
                                                          pol.product_uom.id)
            if float_compare(remaining_qty, remaining_proc_qty_pol_uom,
                             precision_rounding=pol.product_uom.rounding) >= 0:
                procs_for_first_line |= proc
                remaining_qty -= remaining_proc_qty_pol_uom
            else:
                break
        if not dict_procs_lines.get(pol.order_id.id):
            dict_procs_lines[pol.order_id.id] = {}
        if not dict_procs_lines[pol.order_id.id].get(pol.id):
            dict_procs_lines[pol.order_id.id][pol.id] = procs_for_first_line.ids
        else:
            dict_procs_lines[pol.order_id.id][pol.id] += procs_for_first_line.ids
        if procs_for_first_line:
            procurements -= procs_for_first_line
        purchase_lines = purchase_lines[1:]
        return procurements, purchase_lines, dict_procs_lines

    @api.model
    def get_forbidden_order_states_for_proc_assignment(self):
        return ['done', 'cancel']

    @api.multi
    def compute_which_procs_for_lines(self):
        list_products_done = []
        dict_procs_lines = {}
        not_assigned_procs = self.env['procurement.order']
        for rec in self:
            if (rec.product_id, rec.location_id) not in list_products_done:
                procurements = self.env['procurement.order'].search([('id', 'in', self.ids),
                                                                     ('product_id', '=', rec.product_id.id),
                                                                     ('location_id', '=', rec.location_id.id)],
                                                                    order='date_planned asc, product_qty asc')
                # First, let's check running lines
                purchase_lines = self.env['purchase.order.line']. \
                    search([('order_id.state', 'not in', self.get_forbidden_order_states_for_proc_assignment()),
                            ('order_id.state', '!=', 'draft'),
                            ('order_id.location_id', '=', rec.location_id.id),
                            ('product_id', '=', rec.product_id.id),
                            ('remaining_qty', '>', 0)], order='date_planned asc, remaining_qty desc')
                while procurements and purchase_lines:
                    procurements, purchase_lines, dict_procs_lines = procurements. \
                        compute_procs_for_first_line_found(purchase_lines, dict_procs_lines)
                # If some procurements are not assigned yet, we check draft lines
                purchase_lines = procurements and self.env['purchase.order.line']. \
                    search([('order_id.state', 'not in', self.get_forbidden_order_states_for_proc_assignment()),
                            ('order_id.state', '=', 'draft'),
                            ('order_id.location_id', '=', rec.location_id.id),
                            ('product_id', '=', rec.product_id.id),
                            ('remaining_qty', '>', 0)], order='date_planned asc, remaining_qty desc') or False
                while procurements and purchase_lines:
                    purchase_lines = self.env['purchase.order.line']. \
                        search([('order_id.state', 'not in', self.get_forbidden_order_states_for_proc_assignment()),
                                ('order_id.state', '=', 'draft'),
                                ('order_id.location_id', '=', rec.location_id.id),
                                ('product_id', '=', rec.product_id.id),
                                ('remaining_qty', '>', 0)], order='date_planned asc, remaining_qty desc')
                    procurements, purchase_lines, dict_procs_lines = procurements. \
                        compute_procs_for_first_line_found(purchase_lines, dict_procs_lines)
                list_products_done += [(rec.product_id, rec.location_id)]
                not_assigned_procs |= procurements
        return dict_procs_lines, not_assigned_procs

    @api.model
    def get_purchase_line_procurements(self, first_proc, purchase_date, company, seller, order_by, force_domain=None):
        """Returns procurements that must be integrated in the same purchase order line as first_proc, by
        taking all procurements of the same product as first_proc between the date of first proc and date_end.
        """
        procurements_grouping_period = self.env['procurement.order']
        frame = seller.order_group_period
        date_end = False
        if frame and frame.period_type:
            date_end = fields.Datetime.to_string(frame.get_date_end_period(purchase_date))
        domain_procurements = [('product_id', '=', first_proc.product_id.id),
                               ('location_id', '=', first_proc.location_id.id),
                               ('company_id', '=', first_proc.company_id.id),
                               ('date_planned', '>=', first_proc.date_planned)] + (force_domain or [])
        if first_proc.rule_id.picking_type_id:
            domain_procurements += [('rule_id.picking_type_id', '=', first_proc.rule_id.picking_type_id.id)]
        possible_procurements_grouping_period = self.search(domain_procurements, order=order_by)
        for procurement in possible_procurements_grouping_period:
            procurement_schedule_date = self._get_purchase_schedule_date(procurement, company)
            procurement_purchase_date = self._get_purchase_order_date(procurement, company, procurement_schedule_date)
            if not date_end or fields.Datetime.to_string(procurement_purchase_date) <= date_end:
                procurements_grouping_period += procurement
            else:
                break
        line_qty_product_uom = sum([self.env['product.uom'].
                                   _compute_qty(proc.product_uom.id, proc.product_qty,
                                                proc.product_id.uom_id.id) for proc in
                                    procurements_grouping_period]) or 0
        suppliers = first_proc.product_id.seller_ids. \
            filtered(lambda supplier: supplier.name == self.env['procurement.order'].
                     _get_product_supplier(first_proc))
        moq = suppliers and suppliers[0].min_qty or False
        if moq and float_compare(line_qty_product_uom, moq,
                                 precision_rounding=first_proc.product_id.uom_id.rounding) < 0:
            procurements_after_period = self.search(domain_procurements +
                                                    [('id', 'not in', procurements_grouping_period.ids)],
                                                    order=order_by)
            for proc in procurements_after_period:
                proc_qty_product_uom = self.env['product.uom']. \
                    _compute_qty(proc.product_uom.id, proc.product_qty,
                                 proc.product_id.uom_id.id)
                if float_compare(line_qty_product_uom + proc_qty_product_uom, moq,
                                 precision_rounding=proc.product_id.uom_id.rounding) > 0:
                    break
                procurements_grouping_period |= proc
                line_qty_product_uom += proc_qty_product_uom
        return self.search([('id', 'in', procurements_grouping_period.ids)], order=order_by)

    @api.multi
    def get_corresponding_draft_order(self, seller, purchase_date):
        # look for any other draft PO for the same supplier to attach the new line.
        # If no one is found, we create a new draft one
        self.ensure_one()
        days_delta = int(self.env['ir.config_parameter'].
                         get_param('purchase_procurement_just_in_time.delta_begin_grouping_period') or 0)
        main_domain = [('partner_id', '=', seller.id),
                       ('state', '=', 'draft'),
                       ('picking_type_id', '=', self.rule_id.picking_type_id.id),
                       ('location_id', '=', self.location_id.id),
                       ('company_id', '=', self.company_id.id)]
        if self.partner_dest_id:
            main_domain += [('dest_address_id', '=', self.partner_dest_id.id)]
        domain_date_defined = [('date_order', '!=', False),
                               ('date_order', '<=', fields.Datetime.to_string(purchase_date)[:10] + ' 23:59:59'),
                               '|', ('date_order_max', '=', False),
                               ('date_order_max', '>', fields.Datetime.to_string(purchase_date)[:10] + ' 00:00:00')]
        domain_date_not_defined = [('date_order', '=', False)]
        available_draft_po_ids = self.env['purchase.order'].search(main_domain + domain_date_defined)
        draft_order = False
        if available_draft_po_ids:
            return available_draft_po_ids[0]
        frame = seller.order_group_period
        date_ref = seller.schedule_working_days(days_delta, dt.today())
        date_order, date_order_max = (False, False)
        if frame and frame.period_type:
            date_order, date_order_max = frame.get_start_end_dates(purchase_date, date_ref=date_ref)
        if not date_order:
            date_order = dt.now()
        if not date_order_max:
            date_order_max = date_order + relativedelta(years=1200)
        date_order = fields.Datetime.to_string(date_order)
        date_order_max = fields.Datetime.to_string(date_order_max)
        origin = "%s - %s" % (date_order and date_order[:10] or '',
                              date_order_max and date_order_max[:10] or 'infinite')
        if not draft_order:
            available_draft_po_ids = self.env['purchase.order'].search(main_domain + domain_date_not_defined)
            if available_draft_po_ids:
                draft_order = available_draft_po_ids[0]
                draft_order.write({'date_order': date_order,
                                   'date_order_max': date_order_max,
                                   'origin': origin})
        if not draft_order and not seller.nb_max_draft_orders or seller.get_nb_draft_orders() < seller.nb_max_draft_orders:
            name = self.env['ir.sequence'].next_by_code('purchase.order') or _('PO: %s') % self.name
            po_vals = {
                'name': name,
                'origin': origin,
                'partner_id': seller.id,
                'location_id': self.location_id.id,
                'picking_type_id': self.rule_id.picking_type_id.id,
                'pricelist_id': seller.property_product_pricelist_purchase.id,
                'currency_id': seller.property_product_pricelist_purchase and
                               seller.property_product_pricelist_purchase.currency_id.id or
                               self.company_id.currency_id.id,
                'date_order': date_order,
                'date_order_max': date_order_max,
                'company_id': self.company_id.id,
                'fiscal_position': seller.property_account_position and
                                   seller.property_account_position.id or False,
                'payment_term_id': seller.property_supplier_payment_term.id or False,
                'dest_address_id': self.partner_dest_id.id,
            }
            draft_order = self.env['purchase.order'].sudo().create(po_vals)
        return draft_order

    @api.multi
    def group_procurements_by_orders(self):
        dict_lines_to_create = {}
        days_delta = int(self.env['ir.config_parameter'].
                         get_param('purchase_procurement_just_in_time.delta_begin_grouping_period') or 0)
        order_by = 'date_planned asc, product_qty asc, id asc'
        not_assigned_procs = self
        procurements_to_check = self.search([('id', 'in', self.ids)], order=order_by)
        while procurements_to_check:
            first_proc = procurements_to_check[0]
            company = first_proc.company_id
            product = first_proc.product_id
            # Let's process procurements by grouping period
            seller = self.env['procurement.order']._get_product_supplier(first_proc)
            schedule_date = self._get_purchase_schedule_date(first_proc, company)
            purchase_date = self._get_purchase_order_date(first_proc, company, schedule_date)
            pol_procurements = self.get_purchase_line_procurements(
                first_proc, purchase_date, company, seller, order_by,
                force_domain=[('id', 'in', procurements_to_check.ids), ('product_id', '=', product.id)])
            # We consider procurements after the reference date
            # (if we ignore past procurements, past ones are already removed)
            date_ref = seller.schedule_working_days(days_delta, dt.today())
            purchase_date = max(purchase_date, date_ref)
            line_vals = self._get_po_line_values_from_proc(first_proc, seller, company, schedule_date)
            draft_order = first_proc.get_corresponding_draft_order(seller, purchase_date)
            if draft_order and pol_procurements:
                line_vals.update(order_id=draft_order.id, product_qty=0)
                if not dict_lines_to_create.get(draft_order.id):
                    dict_lines_to_create[draft_order.id] = {}
                if not dict_lines_to_create[draft_order.id].get(product.id):
                    dict_lines_to_create[draft_order.id][product.id] = {'vals': line_vals,
                                                                        'procurement_ids': pol_procurements.ids}
                else:
                    dict_lines_to_create[draft_order.id][product.id]['procurement_ids'] += pol_procurements.ids
                not_assigned_procs -= pol_procurements
            procurements_to_check -= pol_procurements
        return not_assigned_procs, dict_lines_to_create

    @api.model
    def create_draft_lines(self, dict_lines_to_create):
        time_begin = dt.now()
        for order_id in dict_lines_to_create.keys():
            for product_id in dict_lines_to_create[order_id].keys():
                line_vals = dict_lines_to_create[order_id][product_id]['vals']
                pol_procurements = self.browse(dict_lines_to_create[order_id][product_id]['procurement_ids'])
                line = self.env['purchase.order.line'].sudo().create(line_vals)
                last_proc = pol_procurements[-1]
                for procurement in pol_procurements:
                    # We compute new qty and new price, and write it only for the last procurement added
                    new_qty, new_price = self.with_context().with_context(focus_on_procurements=True). \
                        _calc_new_qty_price(procurement, po_line=line)
                    procurement.add_proc_to_line(line)
                    if procurement == last_proc and new_qty > line.product_qty:
                        line.sudo().write({'product_qty': new_qty, 'price_unit': new_price})
        return _(u"Order was correctly filled in %s s." % int((dt.now() - time_begin).seconds))

    @api.model
    def launch_draft_lines_creation(self, dict_lines_to_create, return_msg, jobify=False):
        time_now = dt.now()
        fill_orders_in_separate_jobs = bool(self.env['ir.config_parameter'].
                                            get_param('purchase_procurement_just_in_time.fill_orders_in_separate_jobs'))

        if len(dict_lines_to_create.keys()) > 1 and jobify and fill_orders_in_separate_jobs:
            total_number_orders = len(dict_lines_to_create.keys())
            number_order = 0
            for order_id in dict_lines_to_create.keys():
                order = self.env['purchase.order'].browse(order_id)
                number_order += 1
                session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
                seller = self.env['procurement.order']._get_product_supplier(self[0])
                job_create_draft_lines. \
                    delay(session, 'procurement.order', {order_id: dict_lines_to_create[order_id]},
                          description=_("Filling purchase order %s for supplier %s (order %s/%s)") %
                                      (order.name, seller.name, number_order, total_number_orders))
            return_msg += u"\nCreating jobs to fill draft orders: %s s." % int((dt.now() - time_now).seconds)
        else:
            self.create_draft_lines(dict_lines_to_create)
            return_msg += u"\nDraft order(s) filled: %s s." % int((dt.now() - time_now).seconds)
        return return_msg

    @api.multi
    def sanitize_draft_orders(self, company, seller):
        orders = self.env['purchase.order'].search([('state', '=', 'draft'),
                                                    ('partner_id', '=', seller.id),
                                                    ('company_id', '=', company.id)], order='date_order')
        order_lines = self.env['purchase.order.line'].search([('order_id', 'in', orders.ids)])
        procurements = self.env['procurement.order'].search([('purchase_line_id.order_id', 'in', orders.ids)])
        procurements.remove_procs_from_lines()
        order_lines.unlink()
        orders.write({
            'date_order': False,
            'date_order_max': False,
        })

    @api.multi
    def delete_useless_draft_orders(self, companies):
        seller = self.env['procurement.order']._get_product_supplier(self[0])
        for company in companies:
            orders = self.env['purchase.order'].search([('state', '=', 'draft'),
                                                        ('partner_id', '=', seller.id),
                                                        ('date_order', '=', False),
                                                        ('company_id', '=', company.id)])
            orders_to_unlink = self.env['purchase.order']
            for order in orders:
                if not order.order_line:
                    orders_to_unlink |= order
            orders_to_unlink.unlink()

    @api.multi
    def purchase_schedule_procurements(self, jobify=False):
        return_msg = u""
        companies = {proc.company_id for proc in self}
        locations = {proc.location_id for proc in self}
        sellers = {self.env['procurement.order']._get_product_supplier(proc) for proc in self}
        assert len(companies) == 1, "purchase_schedule_procurements should be called with procs of the same company"
        assert len(locations) == 1, "purchase_schedule_procurements should be called with procs of the same location"
        assert len(sellers) == 1, "purchase_schedule_procurements should be called with procs of the same supplier"
        time_now = dt.now()
        self.sanitize_draft_orders([company for company in companies][0], [seller for seller in sellers][0])
        return_msg += u"Sanitizing draft orders: %s s." % int((dt.now() - time_now).seconds)
        time_now = dt.now()
        dict_procs_lines, not_assigned_procs = self.compute_which_procs_for_lines()
        return_msg += u"\nComputing which procs for lines: %s s." % int((dt.now() - time_now).seconds)
        time_now = dt.now()
        not_assigned_procs, dict_lines_to_create = not_assigned_procs.group_procurements_by_orders()
        return_msg += u"\nGrouping unassigned procurements by orders: %s s." % int((dt.now() - time_now).seconds)
        time_now = dt.now()
        self.delete_useless_draft_orders(companies)
        return_msg += u"\nDeleting useless draft orders: %s s." % int((dt.now() - time_now).seconds)
        time_now = dt.now()
        not_assigned_procs.remove_procs_from_lines(unlink_moves_to_procs=True)
        return_msg += u"\nRemoving unsassigned procurements from purchase order lines: %s s." % \
                      int((dt.now() - time_now).seconds)
        # TODO: mettre à jour les message ops
        return_msg = self.env['procurement.order'].prepare_procurements_redistribution(dict_procs_lines, return_msg)
        return_msg = self.env['procurement.order']. \
            launch_procurement_redistribution(dict_procs_lines, return_msg, jobify=jobify)
        return_msg = self.launch_draft_lines_creation(dict_lines_to_create, return_msg, jobify=jobify)
        return return_msg

    @api.multi
    def remove_procs_from_lines(self, unlink_moves_to_procs=False):
        self.remove_done_moves()
        pickings_with_pol = self.search([('id', 'in', self.ids), ('purchase_line_id', '!=', False)])
        pickings_with_pol.with_context(tracking_disable=True).write({'purchase_line_id': False})
        to_reset = self.search([('id', 'in', self.ids), ('state', 'in', ['running', 'exception'])])
        to_reset.with_context(tracking_disable=True).write({'state': 'buy_to_run'})
        procs_moves_to_detach = self.env['stock.move']
        for proc in self:
            if proc.state in ['done', 'cancel']:
                # Done and cancel procs should not change purchase order line
                continue
            proc_moves = self.env['stock.move'].search([('procurement_id', '=', proc.id),
                                                        ('state', 'not in', ['cancel', 'done'])]
                                                       ).with_context(mail_notrack=True)
            if unlink_moves_to_procs:
                # We cancel procurement to cancel previous moves, and keep next ones
                proc_moves.with_context(cancel_procurement=True, mail_notrack=True).action_cancel()
                proc_moves.unlink()
            else:
                procs_moves_to_detach += proc_moves
        procs_moves_to_detach = self.env['stock.move'].search([('id', 'in', procs_moves_to_detach.ids),
                                                               '|', ('purchase_line_id', '!=', False),
                                                               ('picking_id', '!=', False)])
        if procs_moves_to_detach:
            procs_moves_to_detach.write({'purchase_line_id': False, 'picking_id': False})

    @api.multi
    def add_proc_to_line(self, pol):
        pol.ensure_one()
        for rec in self:
            assert rec.state not in ['done', 'cancel']

            orig_pol = rec.purchase_line_id
            rec.remove_procs_from_lines()
            if orig_pol.order_id.state in self.env['purchase.order'].get_purchase_order_states_with_moves():
                orig_pol.adjust_move_no_proc_qty()

            rec.with_context(tracking_disable=True).write({'purchase_line_id': pol.id})
            if not rec.move_ids:
                continue

            assert not any([move.state == 'done' for move in rec.move_ids])
            running_moves = self.env['stock.move'].search([('id', 'in', rec.move_ids.ids),
                                                           ('state', 'not in', ['done', 'cancel'])]
                                                          ).with_context(mail_notrack=True)
            if pol.order_id.state in self.env['purchase.order'].get_purchase_order_states_with_moves():
                group = self.env['procurement.group'].search([('name', '=', pol.order_id.name),
                                                              ('partner_id', '=', pol.order_id.partner_id.id)],
                                                             limit=1)
                if not group:
                    group = self.env['procurement.group'].create({'name': pol.order_id.name,
                                                                  'partner_id': pol.order_id.partner_id.id})
                running_moves.write({'purchase_line_id': pol.id,
                                     'picking_id': False,
                                     'group_id': group.id,
                                     'origin': pol.order_id.name})
                # We try to attach the move to the correct picking (matching new procurement group)
                running_moves.action_confirm()
                running_moves.force_assign()
            else:
                # We attach the proc to a draft line, so we cancel all moves if any
                running_moves.with_context(cancel_procurement=True, tracking_disable=True).action_cancel()
                running_moves.unlink()
        self.with_context(tracking_disable=True).write({'state': 'running'})

    @api.model
    def prepare_procurements_redistribution(self, dict_procs_lines, return_msg):
        time_now = dt.now()
        procs_to_remove_from_lines = self.env['procurement.order']
        for order_id in dict_procs_lines.keys():
            for pol_id in dict_procs_lines[order_id].keys():
                pol = self.env['purchase.order.line'].browse(pol_id)
                procurements = self.browse(dict_procs_lines[order_id][pol_id])
                for proc in pol.procurement_ids:
                    if proc not in procurements:
                        procs_to_remove_from_lines |= proc
        if procs_to_remove_from_lines:
            procs_to_remove_from_lines.remove_procs_from_lines()
        return_msg += u"\nRemoving procs from running lines: %s s." % int((dt.now() - time_now).seconds)
        return return_msg

    @api.model
    def redistribute_procurements_in_lines(self, dict_procs_lines):
        time_now = dt.now()
        for order_id in dict_procs_lines.keys():
            for pol_id in dict_procs_lines[order_id].keys():
                pol = self.env['purchase.order.line'].browse(pol_id)
                procurements = self.browse(dict_procs_lines[order_id][pol_id])
                for proc in procurements:
                    if proc not in pol.procurement_ids:
                        proc.add_proc_to_line(pol)
                if pol.order_id.state in self.env['purchase.order'].get_purchase_order_states_with_moves():
                    pol.adjust_move_no_proc_qty()
        return u"\nAdding procs into running lines and adjusting moves no procs qty for running " \
               u"lines: %s s." % int((dt.now() - time_now).seconds)

    @api.model
    def launch_procurement_redistribution(self, dict_procs_lines, return_msg, jobify=False):
        redistribute_procurements_in_separate_jobs = bool(self.env['ir.config_parameter']. \
            get_param('purchase_procurement_just_in_time.redistribute_procurements_in_separate_jobs'))
        if len(dict_procs_lines.keys()) > 1 and jobify and redistribute_procurements_in_separate_jobs:
            time_now = dt.now()
            total_number_orders = len(dict_procs_lines.keys())
            number_order = 0
            for order_id in dict_procs_lines.keys():
                order = self.env['purchase.order'].browse(order_id)
                number_order += 1
                session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
                job_redistribute_procurements_in_lines. \
                    delay(session, 'procurement.order', {order_id: dict_procs_lines[order_id]},
                          description=_("Redistributing procurements for order %s of supplier %s (order %s/%s)") %
                                      (order.name, order.partner_id.name, number_order, total_number_orders))
            return_msg += u"\nCreating jobs to redistribute procurements %s s." % int((dt.now() - time_now).seconds)
        else:
            return_msg += self.redistribute_procurements_in_lines(dict_procs_lines)
        return return_msg

    @api.multi
    def set_exception_no_supplier(self):
        for rec in self:
            rec.message_post(_("There is no supplier associated to product %s") % (rec.product_id.name))
        self.write({'state': 'exception'})

    @api.multi
    def make_po(self):
        res = {}
        for proc in self:
            if not self.env['procurement.order']._get_product_supplier(proc):
                proc.set_exception_no_supplier()
                res[proc.id] = False
            else:
                res[proc.id] = True
        return res

    @api.multi
    def run(self, autocommit=False):
        res = super(ProcurementOrderPurchaseJustInTime, self).run(autocommit)
        for proc in self:
            if proc.rule_id and proc.rule_id.action == 'buy':
                if proc.state == 'running' and not proc.purchase_line_id:
                    proc.state = 'buy_to_run'
        return res

    @api.model
    def _check(self, procurement):
        if procurement.purchase_line_id:
            if procurement.purchase_line_id.order_id.shipped:
                return True
            elif procurement.move_ids:
                cancel_test_list = [x.state == 'cancel' for x in procurement.move_ids]
                done_cancel_test_list = [x.state in ('done', 'cancel') for x in procurement.move_ids]
                all_done_or_cancel = all(done_cancel_test_list)
                all_cancel = all(cancel_test_list)
                if not all_done_or_cancel:
                    return False
                elif all_done_or_cancel and not all_cancel:
                    return True
                elif all_cancel:
                    procurement.message_post(body=_('All stock moves have been cancelled for this procurement.'))
                    procurement.write({'state': 'cancel'})
                return False
        return super(ProcurementOrderPurchaseJustInTime, self)._check(procurement)
