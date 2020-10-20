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

from datetime import datetime as dt, timedelta

from dateutil.relativedelta import relativedelta
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession, ConnectorSessionHandler

from openerp import modules, models, fields, api, exceptions, _
from openerp.tools.float_utils import float_compare
from openerp.addons.connector.exception import RetryableJobError


@job(default_channel='root.purchase_scheduler')
def job_purchase_schedule(session, model_name, compute_all_products, compute_supplier_ids,
                          compute_product_ids, jobify, force_date_ref=False, force_product_domain=None):
    result = session.env[model_name].launch_purchase_schedule(compute_all_products,
                                                              compute_supplier_ids,
                                                              compute_product_ids,
                                                              jobify,
                                                              force_date_ref=force_date_ref,
                                                              force_product_domain=force_product_domain)
    return result


@job(default_channel='root.purchase_scheduler')
def job_purchase_schedule_seller(session, model_name, seller_id, procurement_ids, jobify,
                                 force_date_ref=False):
    result = session.env[model_name].launch_purchase_schedule_seller(seller_id, procurement_ids, jobify,
                                                                     force_date_ref=force_date_ref)
    return result


@job(default_channel='root.purchase_scheduler')
def job_purchase_schedule_procurements(session, model_name, ids, jobify,
                                       force_date_ref=False):
    result = session.env[model_name].search([('id', 'in', ids)]).with_context(force_date_ref=force_date_ref).\
        purchase_schedule_procurements(jobify)
    return result


@job(default_channel='root.purchase_scheduler')
def job_create_draft_lines(session, model_name, dict_lines_to_create, next_orders_dict=None, job_info=None):
    result = session.env[model_name].with_context(do_not_update_coverage_data=True). \
        create_draft_lines(dict_lines_to_create, next_orders_dict, jobify=True, job_info=job_info)
    return result


@job(default_channel='root.purchase_scheduler')
def job_redistribute_procurements_in_lines(session, model_name, dict_procs_lines):
    result = session.env[model_name].redistribute_procurements_in_lines(dict_procs_lines)
    return result


@job(default_channel='root.purchase_scheduler')
def job_sanitize_draft_orders(session, model_name, seller_id):
    result = session.env[model_name].sanitize_draft_orders(seller_id)
    return result


class ProductSupplierinfoJIT(models.Model):
    _inherit = 'product.supplierinfo'
    _order = 'sequence, id'


class ProcurementOrderPurchaseJustInTime(models.Model):
    _inherit = 'procurement.order'

    state = fields.Selection(selection_add=[('buy_to_run', "Buy rule to run")])
    purchase_line_id = fields.Many2one('purchase.order.line', index=True)
    date_buy_to_run = fields.Datetime(string=u"Date buy to run", copy=False, readonly=True)
    forced_to_done_by_reception = fields.Boolean(string=u"Status forced to done during a reception")

    @api.multi
    def write(self, vals):
        if vals.get('state') == 'buy_to_run':
            vals['date_buy_to_run'] = fields.Datetime.now()
        return super(ProcurementOrderPurchaseJustInTime, self).write(vals)

    @api.model
    def get_delta_begin_grouping_period(self):
        self.env.cr.execute("""SELECT coalesce(VALUE :: INTEGER, 0) AS delta_begin_grouping_period
FROM ir_config_parameter
WHERE key = 'purchase_procurement_just_in_time.delta_begin_grouping_period'""")
        result = self.env.cr.fetchall()
        return result and int(result[0][0]) or 0

    @api.model
    def propagate_cancel(self, procurement):
        """
        Now, the cancelment of a procurement has not any consequence on its purchase order line.
        """
        if procurement.rule_id.action == 'buy' and procurement.purchase_line_id:
            return None
        else:
            return super(ProcurementOrderPurchaseJustInTime, self).propagate_cancel(procurement)

    @api.model
    def _get_product_supplier(self, procurement):
        ''' returns the main supplier of the procurement's product given as argument'''
        company_supplier = procurement.product_id.product_tmpl_id. \
            get_main_supplierinfo(force_company=procurement.company_id)
        if company_supplier:
            return company_supplier.name
        return procurement.product_id.seller_id

    @api.model
    def purchase_schedule(self, compute_all_products=True, compute_supplier_ids=None, compute_product_ids=None,
                          jobify=True, manual=False, force_date_ref=False, force_product_domain=None):
        config_sellers_manually = bool(self.env['ir.config_parameter'].
                                       get_param('purchase_procurement_just_in_time.config_sellers_manually'))
        if manual or not config_sellers_manually:
            compute_supplier_ids = compute_supplier_ids and compute_supplier_ids.ids or []
            compute_product_ids = compute_product_ids and compute_product_ids.ids or []
            session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
            if jobify:
                job_purchase_schedule.delay(session, 'procurement.order', compute_all_products,
                                            compute_supplier_ids, compute_product_ids, jobify,
                                            force_date_ref=force_date_ref,
                                            description=_("Scheduling purchase orders"),
                                            force_product_domain=force_product_domain)
            else:
                job_purchase_schedule(session, 'procurement.order', compute_all_products,
                                      compute_supplier_ids, compute_product_ids, jobify,
                                      force_date_ref=force_date_ref, force_product_domain=force_product_domain)

    @api.model
    def execute_procs_by_seller_query(self, corresponding_products):
        module_path = modules.get_module_path('purchase_procurement_just_in_time')
        with open(module_path + '/sql/' + 'procs_by_seller_query.sql') as sql_file:
            self.env.cr.execute(sql_file.read(), (tuple(corresponding_products.ids or [0]),))

    @api.model
    def launch_purchase_schedule(self, compute_all_products, compute_supplier_ids, compute_product_ids, jobify,
                                 force_date_ref=False, force_product_domain=None):
        corresponding_products = self.env['product.product'].search(force_product_domain or [])
        self.env['product.template'].update_seller_ids()
        self.env.cr.execute("""SELECT sc.id
FROM stock_scheduler_controller sc
  LEFT JOIN queue_job qj ON qj.uuid = sc.job_uuid
WHERE coalesce(sc.done, FALSE) IS FALSE AND
      (coalesce(sc.job_uuid, '') = '' OR
       qj.state NOT IN ('done', 'failed'))""")
        if self.env.cr.fetchall():
            raise RetryableJobError(u"Impossible to launch purchase scheduler when stock scheduler is running",
                                    seconds=1200)
        sellers_to_compute_ids = compute_all_products and \
                                 self.env['res.partner'].search([('supplier', '=', True)]).ids or \
                                 compute_supplier_ids or []
        dict_proc_sellers = {seller_id: [] for seller_id in sellers_to_compute_ids}
        self.execute_procs_by_seller_query(corresponding_products)
        for item in self.env.cr.fetchall():
            if compute_all_products or compute_supplier_ids and item[1] in compute_supplier_ids or compute_product_ids \
                    and item[4] in compute_product_ids:
                if item[1] not in dict_proc_sellers:
                    dict_proc_sellers[item[1]] = []
                dict_proc_sellers[item[1]] += [item[0]]
        for seller_id in dict_proc_sellers.keys():
            procurement_for_seller_ids = dict_proc_sellers[seller_id]
            session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
            supplier = self.env['res.partner'].search([('id', '=', seller_id)])
            seller_ok = supplier._is_valid_supplier_for_scheduler(compute_all_products, compute_supplier_ids)
            if seller_ok:
                if not procurement_for_seller_ids:
                    if jobify:
                        job_sanitize_draft_orders.delay(session, 'procurement.order', seller_id,
                                                        description=_("Deleting draft orders for supplier %s" %
                                                                      supplier.display_name))
                    else:
                        job_sanitize_draft_orders(session, 'procurement.order', seller_id)
                elif jobify:
                    job_purchase_schedule_seller.delay(session, 'procurement.order', seller_id,
                                                       procurement_for_seller_ids, jobify,
                                                       force_date_ref=force_date_ref,
                                                       description=_("Scheduling purchase orders for supplier %s" %
                                                                     supplier.display_name))
                else:
                    job_purchase_schedule_seller(session, 'procurement.order', seller_id, procurement_for_seller_ids,
                                                 jobify, force_date_ref=force_date_ref)

    @api.model
    def get_delivery_date_for_dateref_order(self, product, seller, date_ref):
        supplierinfo = product.get_main_supplierinfo(force_supplier=seller)
        min_date = date_ref
        if supplierinfo:
            min_date = seller.schedule_working_days(product.seller_delay, date_ref)
        return fields.Datetime.to_string(min_date)

    @api.model
    def sanitize_draft_orders(self, seller_id):
        orders = self.env['purchase.order'].search([('state', '=', 'draft'), ('partner_id', '=', seller_id)])
        procurements = self.env['procurement.order'].search([('purchase_line_id.order_id', 'in', orders.ids)])
        procurements.remove_procs_from_lines()
        orders.unlink()
        self.env.invalidate_all()

    @api.model
    def launch_purchase_schedule_seller(self, seller_id, procurement_ids, jobify, force_date_ref=False):
        self.sanitize_draft_orders(seller_id)
        procurements_to_run = self.env['procurement.order'].search([('id', 'in', procurement_ids),
                                                                    ('rule_id.active', '=', True),
                                                                    ('rule_id.picking_type_id.active', '=', True)])
        seller = self.env['res.partner'].search([('id', '=', seller_id)])
        ignore_past_procurements = bool(self.env['ir.config_parameter'].
                                        get_param('purchase_procurement_just_in_time.ignore_past_procurements'))
        config_sellers_manually = bool(self.env['ir.config_parameter'].
                                       get_param('purchase_procurement_just_in_time.config_sellers_manually'))
        suppliers_no_scheduler = config_sellers_manually and self.env['res.partner']. \
            search(['|', '|', ('nb_days_scheduler_frequency', '=', False),
                    ('nb_days_scheduler_frequency', '=', 0),
                    ('next_scheduler_date', '=', False),
                    ('supplier', '=', True)]) or []
        dict_procs = {}
        while procurements_to_run:
            company = procurements_to_run[0].company_id
            product = procurements_to_run[0].product_id
            location = procurements_to_run[0].location_id
            domain = [('id', 'in', procurements_to_run.ids),
                      ('company_id', '=', company.id),
                      ('product_id', '=', product.id),
                      ('location_id', '=', location.id)]
            if not seller:
                # If the first proc has no seller, then we drop this proc and go to the next
                procurements_exception = self.search(domain + [('purchase_line_id', '=', False)])
                procurements_exception.set_exception_for_procs()
                procurements_to_run -= self.search(domain)
                continue
            if seller in suppliers_no_scheduler:
                procurements_exception = self.search(domain + [('purchase_line_id', '=', False)])
                msg = _("Purchase scheduler is not configurated for this supplier")
                procurements_exception.set_exception_for_procs(msg)
                procurements_to_run -= self.search(domain)
                continue
            if ignore_past_procurements:
                days_delta = self.get_delta_begin_grouping_period()
                date_ref = force_date_ref and fields.Datetime.from_string(force_date_ref + ' 06:00:00') or \
                    seller.schedule_working_days(days_delta, dt.today())
                min_draft_procurements_date = self.get_delivery_date_for_dateref_order(product, seller, date_ref)
                first_purchase_line_to_receive = self.env['purchase.order.line']. \
                    search([('order_id.state', 'in', self.env['purchase.order'].get_purchase_order_states_to_receive()),
                            ('product_id', '=', product.id),
                            ('remaining_qty', '>', 0)], order='date_planned asc', limit=1)
                min_date = min_draft_procurements_date
                # Even if we ignore past procurements, procurements before the first possible reception date must be
                # able to be linked to a confirmed order.
                if first_purchase_line_to_receive and \
                        first_purchase_line_to_receive.date_planned < min_draft_procurements_date:
                    min_date = first_purchase_line_to_receive.date_planned
                past_procurements = self.search(domain + [('date_planned', '<=', min_date)])
                if past_procurements:
                    past_procurements.remove_procs_from_lines()
                    procurements_to_run -= past_procurements
                domain += [('date_planned', '>', min_date)]
            procurements = self.search(domain)
            if procurements:
                if not dict_procs.get(company):
                    dict_procs[company] = {}
                if not dict_procs[company].get(location):
                    dict_procs[company][location] = procurements
                else:
                    dict_procs[company][location] += procurements
            procurements_to_run -= procurements
        for company in dict_procs.keys():
            for location in dict_procs[company].keys():
                procurements = dict_procs[company][location]
                if procurements:
                    session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
                    if jobify:
                        job_purchase_schedule_procurements. \
                            delay(session, 'procurement.order', procurements.ids, jobify,
                                  force_date_ref=force_date_ref,
                                  description=_("Scheduling purchase orders for seller %s, "
                                                "company %s and location %s") %
                                  (seller.display_name, company.display_name, location.display_name))
                    else:
                        job_purchase_schedule_procurements(session, 'procurement.order', procurements.ids, jobify,
                                                           force_date_ref=force_date_ref)

    @api.model
    def compute_procs_for_first_line_found(self, procurements, purchase_line_ids, dict_procs_lines):
        pol = self.env['purchase.order.line'].search([('id', '=', purchase_line_ids[0])])
        procs_for_first_line_ids = self.env['procurement.order'].search([('purchase_line_id', '=', pol.id),
                                                                         ('state', 'in', ['done', 'cancel'])]).ids
        remaining_qty = pol.remaining_qty
        for proc in procurements:
            proc_qty_pol_uom = self.env['product.uom']._compute_qty(proc['product_uom'],
                                                                    proc['product_qty'],
                                                                    pol.product_uom.id)
            if float_compare(remaining_qty, proc_qty_pol_uom, precision_rounding=pol.product_uom.rounding) >= 0:
                procs_for_first_line_ids += [proc['id']]
                remaining_qty -= proc_qty_pol_uom
            else:
                if float_compare(remaining_qty, 0, precision_rounding=pol.product_uom.rounding) > 0:
                    pol_remaining_qty_proc_uom = self.env['product.uom']._compute_qty(pol.product_uom.id,
                                                                                      remaining_qty,
                                                                                      proc['product_uom'])
                    old_proc = self.env['procurement.order'].search([("id", "=", proc['id'])])[0]
                    new_proc = old_proc.split(pol_remaining_qty_proc_uom,
                                              force_move_dest_id=old_proc.move_dest_id.id,
                                              force_state=old_proc.state)
                    procs_for_first_line_ids += [new_proc.id]
                    proc['product_qty'] = old_proc.product_qty
                    remaining_qty -= remaining_qty
                break
        if not dict_procs_lines.get(pol.order_id.id):
            dict_procs_lines[pol.order_id.id] = {}
        if not dict_procs_lines[pol.order_id.id].get(pol.id):
            dict_procs_lines[pol.order_id.id][pol.id] = procs_for_first_line_ids
        else:
            dict_procs_lines[pol.order_id.id][pol.id] += procs_for_first_line_ids
        if procs_for_first_line_ids:
            procurements = [proc for proc in procurements if proc['id'] not in procs_for_first_line_ids]
        purchase_line_ids = purchase_line_ids[1:]
        return procurements, purchase_line_ids, dict_procs_lines

    @api.model
    def get_forbidden_order_states_for_proc_assignment(self):
        return ['done', 'cancel']

    @api.model
    def get_dict_ordered_procs_by_product(self, procurement_ids, order_by):
        if not procurement_ids:
            return {}
        dict_ordered_procs_by_product = {}
        ORDER_BY_CLAUSE = """
ORDER BY %s""" % order_by
        self.env.cr.execute("""SELECT
  po.id,
  po.product_id,
  po.product_qty,
  po.product_uom,
  po.date_planned
FROM procurement_order po
WHERE po.id IN %s""" + ORDER_BY_CLAUSE, (tuple(procurement_ids),))
        for item in self.env.cr.dictfetchall():
            if item['product_id'] not in dict_ordered_procs_by_product:
                dict_ordered_procs_by_product[item['product_id']] = []
            dict_ordered_procs_by_product[item['product_id']] += [{'id': item['id'],
                                                                   'product_id': item['product_id'],
                                                                   'product_qty': item['product_qty'],
                                                                   'product_uom': item['product_uom'],
                                                                   'date_planned': item['date_planned']}]
        return dict_ordered_procs_by_product

    @api.model
    def compute_which_procs_for_lines(self, procurement_ids, company, location):
        dict_procs_lines = {}
        not_assigned_proc_ids = []
        if not procurement_ids:
            return dict_procs_lines, not_assigned_proc_ids
        forbidden_order_states = self.get_forbidden_order_states_for_proc_assignment()
        dict_ordered_procs_by_product = self.get_dict_ordered_procs_by_product(procurement_ids,
                                                                               order_by='date_planned, product_qty')
        ORDER_BY_CLAUSE_FOR_LINES = """
ORDER BY pol.date_planned ASC, pol.remaining_qty DESC"""
        for product_id, corresponding_procurements in dict_ordered_procs_by_product.items():
            # First, let's check running lines
            ORDER_LINES_QUERY = """SELECT pol.id
FROM purchase_order_line pol
  LEFT JOIN purchase_order po ON po.id = pol.order_id
WHERE po.state NOT IN %s AND
      coalesce(pol.remaining_qty, 0) > 0 AND
      po.company_id = %s AND
      po.location_id = %s AND
      pol.product_id = %s"""
            self.env.cr.execute(ORDER_LINES_QUERY + """ AND po.state != 'draft'""" + ORDER_BY_CLAUSE_FOR_LINES,
                                (tuple(forbidden_order_states), company.id, location.id, product_id,))
            purchase_line_ids = [item[0] for item in self.env.cr.fetchall()]
            while corresponding_procurements and purchase_line_ids:
                corresponding_procurements, purchase_line_ids, dict_procs_lines = self. \
                    compute_procs_for_first_line_found(corresponding_procurements, purchase_line_ids, dict_procs_lines)
            # If some procurements are not assigned yet, we check draft lines
            self.env.cr.execute(ORDER_LINES_QUERY + """ AND po.state = 'draft'""" + ORDER_BY_CLAUSE_FOR_LINES,
                                (tuple(forbidden_order_states), company.id, location.id, product_id,))
            purchase_line_ids = [item[0] for item in self.env.cr.fetchall()]
            while corresponding_procurements and purchase_line_ids:
                corresponding_procurements, purchase_line_ids, dict_procs_lines = self. \
                    compute_procs_for_first_line_found(corresponding_procurements, purchase_line_ids, dict_procs_lines)
            not_assigned_proc_ids += [proc['id'] for proc in corresponding_procurements]
        return dict_procs_lines, not_assigned_proc_ids

    @api.multi
    def get_end_date_for_procs_grouping_period(self, seller, purchase_date, company, date_ref):
        self.ensure_one()
        orders_filling_mode = self.env['ir.config_parameter']. \
            get_param('purchase_procurement_just_in_time.orders_filling_mode') or 'fixed_date_delivery'
        frame = seller.get_effective_order_group_period()
        date_end = False
        if frame and frame.period_type:
            if orders_filling_mode == 'fixed_date_delivery':
                _, date_end = frame.get_start_end_dates(purchase_date, date_ref=date_ref)
            else:
                date_end = frame.get_date_end_period(purchase_date)
        end_date_planned = False
        if date_end:
            end_schedule_date = self._get_purchase_order_date(self, company, date_end, reverse=True)
            end_schedule_date = fields.Datetime.to_string(end_schedule_date)
            end_date_planned = self._get_purchase_schedule_date(self, company, ref_date=end_schedule_date, reverse=True)
            end_date_planned = fields.Datetime.to_string(end_date_planned)
        return end_date_planned

    @api.multi
    def add_procs_to_reach_moq(self, seller, procurements_grouping_period, procurements_after_period):
        self.ensure_one()
        product_uom_id = self.product_id.uom_id.id
        product_uom_rounding = self.product_id.uom_id.rounding
        line_qty_product_uom = sum([self.env['product.uom'].
                                   _compute_qty(proc['product_uom'], proc['product_qty'], product_uom_id) for proc in
                                    procurements_grouping_period]) or 0
        supplierinfo = self.env['product.supplierinfo'].search([('id', 'in', self.product_id.seller_ids.ids),
                                                                ('name', '=', seller and seller.id or False)],
                                                               order='sequence, id', limit=1)
        moq = supplierinfo and supplierinfo.min_qty or False
        next_proc_group_planned_date = procurements_after_period and \
            procurements_after_period[0]['date_planned'] or None
        if moq and float_compare(line_qty_product_uom, moq,
                                 precision_rounding=product_uom_rounding) < 0:
            for proc in procurements_after_period:
                proc_qty_product_uom = self.env['product.uom']._compute_qty(proc['product_uom'],
                                                                            proc['product_qty'],
                                                                            product_uom_id)
                if float_compare(line_qty_product_uom + proc_qty_product_uom, moq,
                                 precision_rounding=product_uom_rounding) > 0:
                    next_proc_group_planned_date = proc['date_planned']
                    break
                line_qty_product_uom += proc_qty_product_uom
                procurements_grouping_period += [proc]
        return procurements_grouping_period, next_proc_group_planned_date

    @api.model
    def get_purchase_line_procurements(self, procurement_dicts, purchase_date, company, seller, order_by, date_ref):
        """Returns procurements that must be integrated in the same purchase order line as first_proc, by
        taking all procurements of the same product as first_proc between the date of first proc and date_end.
        """
        first_proc = self.browse(procurement_dicts[0]['id'])
        end_date_planned = first_proc.get_end_date_for_procs_grouping_period(seller, purchase_date, company, date_ref)
        procurements_grouping_period = procurement_dicts
        if end_date_planned:
            procurements_grouping_period = [proc for proc in procurement_dicts if
                                            proc['date_planned'] <= end_date_planned]
        procurements_grouping_period_ids = [proc['id'] for proc in procurements_grouping_period]
        procurements_after_period = [proc for proc in procurement_dicts if
                                     proc['id'] not in procurements_grouping_period_ids]
        procurements_grouping_period, next_proc_group_planned_date = first_proc. \
            add_procs_to_reach_moq(seller, procurements_grouping_period, procurements_after_period)
        procurements_grouping_period_ids = [proc['id'] for proc in procurements_grouping_period]
        return procurements_grouping_period_ids, next_proc_group_planned_date

    @api.multi
    def get_corresponding_draft_order_main_domain(self, seller):
        self.ensure_one()
        main_domain = [('partner_id', '=', seller.id),
                       ('state', '=', 'draft'),
                       ('picking_type_id', '=', self.rule_id.picking_type_id.id),
                       ('location_id', '=', self.location_id.id),
                       ('company_id', '=', self.company_id.id)]
        if self.partner_dest_id:
            main_domain += [('dest_address_id', '=', self.partner_dest_id.id)]
        return main_domain

    @api.multi
    def get_corresponding_draft_order_values(self, name, origin, seller, date_order, date_order_max):
        self.ensure_one()
        return {
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
            'is_created_by_admin': True,
        }

    @api.multi
    def get_corresponding_draft_order(self, seller, purchase_date):
        # look for any other draft PO for the same supplier to attach the new line.
        # If no one is found, we create a new draft one
        self.ensure_one()
        force_creation = self.env.context.get('force_creation')
        forbid_creation = self.env.context.get('forbid_creation')
        force_date_ref = self.env.context.get('force_date_ref')
        days_delta = self.get_delta_begin_grouping_period()
        draft_order = self.env['purchase.order']
        if not force_creation:
            main_domain = self.get_corresponding_draft_order_main_domain(seller)
            domain_date_defined = [('date_order', '!=', False),
                                   ('date_order', '<=', fields.Datetime.to_string(purchase_date)[:10] + ' 23:59:59'),
                                   '|', ('date_order_max', '=', False),
                                   ('date_order_max', '>', fields.Datetime.to_string(purchase_date)[:10] + ' 00:00:00')]
            available_draft_po = self.env['purchase.order'].search(main_domain + domain_date_defined, limit=1)
            if available_draft_po:
                return available_draft_po
        frame = seller.get_effective_order_group_period()
        date_ref = force_date_ref and fields.Datetime.from_string(force_date_ref + ' 06:00:00') or seller.schedule_working_days(days_delta, dt.today())
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
        allowed_creation = not seller.nb_max_draft_orders or seller.get_nb_draft_orders() < seller.nb_max_draft_orders
        if not draft_order and (allowed_creation or force_creation) and not forbid_creation:
            name = self.env['ir.sequence'].next_by_code('purchase.order') or _('PO: %s') % self.name
            po_vals = self.get_corresponding_draft_order_values(name, origin, seller, date_order, date_order_max)
            draft_order = self.env['purchase.order'].sudo().create(po_vals)
        return draft_order

    @api.multi
    def group_procurements_by_orders(self, seller, company):
        if not self:
            return self, {}
        dict_lines_to_create = {}
        days_delta = self.get_delta_begin_grouping_period()
        order_by = 'date_planned asc, product_qty asc, id asc'
        not_assigned_procs = self
        dict_ordered_procs_by_product = self.get_dict_ordered_procs_by_product(self.ids, order_by=order_by)
        nb_draft_orders = 0
        force_date_ref = self.env.context.get('force_date_ref')
        date_ref = force_date_ref and fields.Datetime.from_string(force_date_ref + ' 06:00:00') or \
            seller.schedule_working_days(days_delta, dt.today())
        for product_id, procurement_dicts in dict_ordered_procs_by_product.iteritems():
            if not procurement_dicts:
                continue
            while procurement_dicts:
                first_proc = self.browse(procurement_dicts[0]['id'])
                product = first_proc.product_id
                # Let's process procurements by grouping period
                schedule_date = self.env['procurement.order']._get_purchase_schedule_date(first_proc, company)
                if schedule_date <= date_ref:
                    purchase_date = date_ref
                else:
                    purchase_date = self.env['procurement.order']. \
                        _get_purchase_order_date(first_proc, company, schedule_date)
                    purchase_date = max(purchase_date, date_ref)
                pol_procurement_ids, next_proc_group_planned_date = self.env['procurement.order']. \
                    get_purchase_line_procurements(procurement_dicts, purchase_date, company,
                                                   seller, order_by, date_ref)
                forbid_creation = bool(seller.nb_max_draft_orders)
                draft_order = first_proc.with_context(forbid_creation=forbid_creation). \
                    get_corresponding_draft_order(seller, purchase_date)
                if draft_order and pol_procurement_ids:
                    force_fiscal_position_id = draft_order.fiscal_position and draft_order.fiscal_position.id or False
                    line_vals = self.env['procurement.order']. \
                        with_context(force_fiscal_position_id=force_fiscal_position_id,
                                     force_date_for_partnerinfo_validity=fields.Date.today()). \
                        _get_po_line_values_from_proc(first_proc, seller, company, schedule_date)
                    line_vals.update(order_id=draft_order.id, product_qty=0)
                    if not dict_lines_to_create.get(draft_order.id):
                        nb_draft_orders += 1
                        dict_lines_to_create[draft_order.id] = {}
                    if not dict_lines_to_create[draft_order.id].get(product.id):
                        dict_lines_to_create[draft_order.id][product.id] = {'vals': line_vals,
                                                                            'procurement_ids': pol_procurement_ids}
                    else:
                        dict_lines_to_create[draft_order.id][product.id]['procurement_ids'] += pol_procurement_ids
                    not_assigned_procs -= self.browse(pol_procurement_ids)
                    if forbid_creation and nb_draft_orders == seller.nb_max_draft_orders:
                        procurement_dicts = []
                        continue
                if not draft_order and forbid_creation:
                    procurement_dicts = []
                else:
                    procurement_dicts = [proc for proc in procurement_dicts if proc['id'] not in pol_procurement_ids]
        return not_assigned_procs, dict_lines_to_create

    @api.model
    def create_draft_lines(self, dict_lines_to_create, next_orders_dict=None, jobify=False, job_info=None):
        time_begin = dt.now()
        #  dict_lines_to_create[draft_order.id][product.id]['procurement_ids']
        for order_id in dict_lines_to_create.keys():
            for product_id in dict_lines_to_create[order_id].keys():
                line_vals = dict_lines_to_create[order_id][product_id]['vals']
                pol_procurements = self.search([('id', 'in',
                                                 dict_lines_to_create[order_id][product_id]['procurement_ids'])])
                line = self.env['purchase.order.line'].with_context(check_product_qty=False).sudo().create(line_vals)
                last_proc = pol_procurements[-1]
                for procurement in pol_procurements:
                    # We compute new qty and new price, and write it only for the last procurement added
                    new_qty, new_price = self.with_context().with_context(focus_on_procurements=True). \
                        _calc_new_qty_price(procurement, po_line=line)
                    procurement.with_context(check_product_qty=False).add_proc_to_line(line)
                    if procurement == last_proc and new_qty > line.product_qty:
                        line.sudo().write({'product_qty': new_qty, 'price_unit': new_price})
            self.env['purchase.order'].browse(order_id).compute_coverage_state()
        if jobify and next_orders_dict:
            order_id = next_orders_dict.keys()[0]
            first_order_dict = {order_id: next_orders_dict[order_id]}
            next_orders_dict.pop(order_id)
            job_info.update(number_order=job_info['number_order'] + 1)
            order = self.env['purchase.order'].search([('id', '=', order_id)])
            session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
            job_create_draft_lines. \
                delay(session, 'procurement.order', first_order_dict, next_orders_dict, job_info,
                      description=_("Filling purchase order %s for supplier %s (order %s/%s)") %
                                   (order.name, job_info['seller_name'], job_info['number_order'] - 1,
                                    job_info['total_number_orders']),
                      )
        return _(u"Order was correctly filled in %s s." % int((dt.now() - time_begin).seconds))

    @api.model
    def launch_draft_lines_creation(self, seller, dict_lines_to_create, return_msg, jobify=False):
        time_now = dt.now()
        fill_orders_in_separate_jobs = bool(self.env['ir.config_parameter'].
                                            get_param('purchase_procurement_just_in_time.fill_orders_in_separate_jobs'))

        if jobify and fill_orders_in_separate_jobs and dict_lines_to_create:
            #  we launch a job to create the first line, this job will pop a job to create next line
            #  we avoid launching create job in parallell because the compute_coverage_state() may takes up to 6 mins
            total_number_orders = len(dict_lines_to_create.keys())
            order_id = dict_lines_to_create.keys()[0]
            first_order_dict = {order_id: dict_lines_to_create[order_id]}
            dict_lines_to_create.pop(order_id)
            order = self.env['purchase.order'].search([('id', '=', order_id)])
            session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
            job_create_draft_lines. \
                delay(session, 'procurement.order', first_order_dict,
                      dict_lines_to_create, {'seller_name': seller.name,
                                             'total_number_orders': total_number_orders,
                                             'number_order': 2},
                      description=_("Filling purchase order %s for supplier %s (order %s/%s)") %
                                   (order.name, seller.name, 1, total_number_orders)
                      )
            return_msg += u"\nCreating job to pop job to fill draft orders: %s s." % int((dt.now() - time_now).seconds)
        else:
            self.with_context(do_not_update_coverage_data=True).create_draft_lines(dict_lines_to_create)
            return_msg += u"\nDraft order(s) filled: %s s." % int((dt.now() - time_now).seconds)
        return return_msg

    @api.model
    def get_query_product_supplierinfo_restricted(self):
        return """product_supplierinfo_restricted AS (
      SELECT *
      FROM product_supplierinfo
      WHERE product_tmpl_id IN (SELECT id
                                FROM product_template_restricted) AND
            name = %s AND COALESCE(active, FALSE) IS TRUE),"""

    @api.multi
    def get_first_date_planned_by_delay(self, seller):
        if not self:
            return {}
        query_product_supplierinfo_restricted = self.get_query_product_supplierinfo_restricted()
        self.env.cr.execute("""WITH procurement_order_restricted AS (
    SELECT *
    FROM procurement_order
    WHERE id IN %s),

    product_product_restricted AS (
      SELECT *
      FROM product_product
      WHERE id IN (SELECT product_id
                   FROM procurement_order_restricted)),

    product_template_restricted AS (
      SELECT *
      FROM product_template
      WHERE id IN (SELECT product_tmpl_id
                   FROM product_product_restricted)),

""" + query_product_supplierinfo_restricted + """

    main_supplier_table_intermediate AS (
      SELECT
        pt.id            AS product_tmpl_id,
        min(ps.sequence) AS sequence
      FROM product_template_restricted pt
        LEFT JOIN product_supplierinfo_restricted ps ON ps.product_tmpl_id = pt.id
      GROUP BY pt.id),

    main_supplier_s AS (
      SELECT
        ps.product_tmpl_id,
        ps.min_qty             AS moq,
        ps.delay,
        ROW_NUMBER()
        OVER (
          PARTITION BY ps.product_tmpl_id
          ORDER BY ps.id ASC ) AS constr
      FROM
        product_supplierinfo_restricted ps
        INNER JOIN
        main_supplier_table_intermediate ms ON ps.product_tmpl_id = ms.product_tmpl_id AND ps.sequence = ms.sequence),

    fournisseur AS (
      SELECT
        product_tmpl_id,
        moq,
        delay
      FROM main_supplier_s
      WHERE main_supplier_s.constr = 1),

    procurement_order_with_delays AS (
      SELECT
        po.*,
        f.delay
      FROM procurement_order_restricted po
        LEFT JOIN product_product pp ON pp.id = po.product_id
        LEFT JOIN fournisseur f ON f.product_tmpl_id = pp.product_tmpl_id),

    first_dates_by_delays AS (
      SELECT
        po.company_id,
        po.location_id,
        po.delay,
        min(po.date_planned) AS first_date_planned_for_delay
      FROM procurement_order_with_delays po
      GROUP BY po.company_id, po.location_id, po.delay)

SELECT
  fd.*,
  min(po.id) AS first_proc_id
FROM first_dates_by_delays fd
  LEFT JOIN procurement_order_with_delays po ON po.company_id = fd.company_id AND
                                                po.location_id = fd.location_id AND
                                                po.delay = fd.delay AND
                                                po.date_planned = fd.first_date_planned_for_delay
GROUP BY fd.company_id, fd.location_id, fd.delay, fd.first_date_planned_for_delay
ORDER BY fd.delay DESC""", (tuple(self.ids), seller.id,))
        return self.env.cr.dictfetchall()

    @api.multi
    def get_first_purchase_dates_for_seller(self, seller):
        # Let's process procurements by delivery lead time, and compute the first purchase date for each
        # company/location.
        first_purchase_dates = {}
        days_delta = self.get_delta_begin_grouping_period()
        force_date_ref = self.env.context.get('force_date_ref')
        first_date_planned_by_delay = self.get_first_date_planned_by_delay(seller)
        date_ref = force_date_ref or fields.Datetime.to_string(seller.schedule_working_days(days_delta, dt.today()))
        while first_date_planned_by_delay:
            item = first_date_planned_by_delay[0]
            first_date_planned_by_delay = first_date_planned_by_delay[1:]
            company_id = item['company_id']
            location_id = item['location_id']
            first_date_planned_for_delay = item['first_date_planned_for_delay']
            first_proc_id = item['first_proc_id']
            if company_id not in first_purchase_dates:
                first_purchase_dates[company_id] = {}
            if location_id not in first_purchase_dates[company_id]:
                first_purchase_dates[company_id][location_id] = {'first_purchase_date': False,
                                                                 'definitive': False,
                                                                 'procurement': self.env['procurement.order']}
            if first_purchase_dates[company_id][location_id]['definitive']:
                continue
            first_purchase_date = first_purchase_dates[company_id][location_id]['first_purchase_date']
            first_proc = self.search([('id', '=', first_proc_id)])
            company = self.env['res.company'].search([('id', '=', company_id)])
            schedule_date = self._get_purchase_schedule_date(first_proc, company)
            purchase_date = self._get_purchase_order_date(first_proc, company, schedule_date)
            if not purchase_date:
                continue
            purchase_date = fields.Datetime.to_string(purchase_date)
            if not first_purchase_date or purchase_date < first_purchase_date:
                first_purchase_dates[company_id][location_id]['first_purchase_date'] = purchase_date
                first_purchase_dates[company_id][location_id]['procurement'] = first_proc
                first_purchase_date = purchase_date
                if first_purchase_date:
                    first_date_planned_by_delay = [item for item in first_date_planned_by_delay if
                                                   item['first_date_planned_for_delay'] < first_date_planned_for_delay]
            if first_purchase_date and first_purchase_date < date_ref:
                first_purchase_dates[company_id][location_id]['first_purchase_date'] = date_ref
                first_purchase_dates[company_id][location_id]['procurement'] = first_proc
                first_purchase_dates[company_id][location_id]['definitive'] = True
        return first_purchase_dates

    @api.multi
    def create_nb_max_draft_orders(self, seller, first_purchase_date):
        self.ensure_one()
        nb_orders = 0
        ref_date = fields.Datetime.from_string(first_purchase_date)
        while nb_orders < seller.nb_max_draft_orders:
            nb_orders += 1
            latest_order = self.with_context(force_creation=True).get_corresponding_draft_order(seller, ref_date)
            assert latest_order, "Impossible to create draft purchase order for purchase date %s" % \
                fields.Datetime.to_string(ref_date)
            assert latest_order.date_order_max, "Impossible to determine end grouping period for start date %s" % \
                latest_order.date_order
            ref_date = fields.Datetime.from_string(latest_order.date_order_max) + timedelta(days=1)

    @api.multi
    def check_procs_same_companies(self):
        self.env.cr.execute("""SELECT company_id
FROM procurement_order
WHERE id IN %s
GROUP BY company_id""", (tuple(self.ids),))
        fetchall = self.env.cr.fetchall()
        assert len(fetchall) == 1, "purchase_schedule_procurements should be called with procs of the same company"
        company_id = fetchall[0][0]
        company = self.env['res.company'].search([('id', '=', company_id)])
        return company

    @api.multi
    def check_procs_same_locations(self):
        self.env.cr.execute("""SELECT location_id
FROM procurement_order
WHERE id IN %s
GROUP BY location_id""", (tuple(self.ids),))
        fetchall = self.env.cr.fetchall()
        assert len(fetchall) == 1, "purchase_schedule_procurements should be called with procs of the same location"
        location_id = fetchall[0][0]
        location = self.env['stock.location'].search([('id', '=', location_id)])
        return location

    @api.multi
    def check_procs_same_sellers(self, seller):
        # We check only procurements linked to products with no supplierinfo or supplierinfos of wrong seller
        seller.ensure_one()
        self.env.cr.execute("""SELECT min(po.id) AS procurement_id
FROM procurement_order po
  LEFT JOIN product_product pp ON pp.id = po.product_id
  LEFT JOIN product_supplierinfo ps ON ps.product_tmpl_id = pp.product_tmpl_id
WHERE po.id IN %s AND (ps.name IS NULL OR ps.name != %s) AND COALESCE(ps.active, FALSE) IS TRUE
GROUP BY po.company_id, po.product_id""", (tuple(self.ids), seller.id,))
        for line in self.env.cr.dictfetchall():
            proc = self.browse(line['procurement_id'])
            proc_seller = self.env['procurement.order']._get_product_supplier(proc)
            if not proc_seller or proc_seller != seller:
                raise exceptions.except_orm(u"Error!", u"purchase_schedule_procurements should be called with procs "
                                                       u"of the same supplier")
        return seller

    @api.model
    def remove_past_procurements_if_needed(self, not_assigned_proc_ids, seller):
        if not not_assigned_proc_ids:
            return
        ignore_past_procurements = bool(self.env['ir.config_parameter'].
                                        get_param('purchase_procurement_just_in_time.ignore_past_procurements'))
        days_delta = self.get_delta_begin_grouping_period()
        force_date_ref = self.env.context.get('force_date_ref')
        date_ref = force_date_ref and fields.Datetime.from_string(force_date_ref + ' 06:00:00') or \
                   seller.schedule_working_days(days_delta, dt.today())
        # If we ignore past procurements, first procurements to create draft orders must be after the first possible
        # reception date
        if ignore_past_procurements:
            self.env.cr.execute("""SELECT product_id
FROM procurement_order
WHERE id IN %s
GROUP BY product_id""", (tuple(not_assigned_proc_ids),))
            product_ids = [item[0] for item in self.env.cr.fetchall()]
            for product in self.env['product.product'].search([('id', 'in', product_ids)]):
                min_draft_procurements_date = self.get_delivery_date_for_dateref_order(product, seller, date_ref)
                procurements_to_remove_ids = self.search([('id', 'in', not_assigned_proc_ids),
                                                          ('date_planned', '<', min_draft_procurements_date)]).ids
                if procurements_to_remove_ids:
                    not_assigned_proc_ids = [proc_id for proc_id in not_assigned_proc_ids if
                                             proc_id not in procurements_to_remove_ids]
        return not_assigned_proc_ids

    @api.multi
    def purchase_schedule_procurements(self, jobify=False):
        return_msg = u""
        time_now = dt.now()
        if not self:
            return return_msg
        company = self.check_procs_same_companies()
        location = self.check_procs_same_locations()
        seller = self.env['procurement.order']._get_product_supplier(self[0])
        self.check_procs_same_sellers(seller)
        return_msg += u"Checking same company, location and seller: %s s." % int((dt.now() - time_now).seconds)
        time_now = dt.now()
        dict_procs_lines, not_assigned_proc_ids = self.compute_which_procs_for_lines(self.ids, company, location)
        return_msg += u"\nComputing which procs for lines: %s s." % int((dt.now() - time_now).seconds)
        not_assigned_proc_ids = self.remove_past_procurements_if_needed(not_assigned_proc_ids, seller)
        time_now = dt.now()
        if seller.nb_max_draft_orders and seller.get_effective_order_group_period() and not_assigned_proc_ids:
            not_assigned_procs = self.env['procurement.order'].search([('id', 'in', not_assigned_proc_ids)])
            first_purchase_dates = not_assigned_procs.with_context(force_partner_id=seller.id). \
                get_first_purchase_dates_for_seller(seller)
            for company_id in first_purchase_dates:
                for location_id in first_purchase_dates[company_id]:
                    first_purchase_date = first_purchase_dates[company_id][location_id]['first_purchase_date']
                    procurement = first_purchase_dates[company_id][location_id]['procurement']
                    procurement.create_nb_max_draft_orders(seller, first_purchase_date)
        return_msg += u"\nCreating draft orders if needed: %s s." % int((dt.now() - time_now).seconds)
        time_now = dt.now()
        not_assigned_procs = self.browse(not_assigned_proc_ids)
        not_assigned_procs, dict_lines_to_create = not_assigned_procs.with_context(force_partner_id=seller.id). \
            group_procurements_by_orders(seller, company)
        return_msg += u"\nGrouping unassigned procurements by orders: %s s." % int((dt.now() - time_now).seconds)
        time_now = dt.now()
        if not_assigned_procs:
            not_assigned_procs.remove_procs_from_lines()
        return_msg += u"\nRemoving unsassigned procurements from purchase order lines: %s s." % \
                      int((dt.now() - time_now).seconds)
        return_msg = self.env['procurement.order'].prepare_procurements_redistribution(dict_procs_lines, return_msg)
        return_msg = self.env['procurement.order']. \
            launch_procurement_redistribution(dict_procs_lines, return_msg, jobify=jobify)
        return_msg = self.launch_draft_lines_creation(seller, dict_lines_to_create, return_msg, jobify=jobify)
        return return_msg

    @api.multi
    def remove_procs_from_lines(self):
        if not self:
            return
        procs_with_pol = self.search([('id', 'in', self.ids), ('purchase_line_id', '!=', False)])
        procs_with_pol.with_context(tracking_disable=True).write({'purchase_line_id': False})
        to_reset = self.search([('id', 'in', self.ids), ('state', 'in', ['running', 'exception'])])
        to_reset.with_context(tracking_disable=True).write({'state': 'buy_to_run'})

    @api.multi
    def add_proc_to_line(self, pol):
        pol.ensure_one()
        self.remove_procs_from_lines()
        self.with_context(tracking_disable=True).write({'purchase_line_id': pol.id, 'state': 'running'})

    @api.model
    def prepare_procurements_redistribution(self, dict_procs_lines, return_msg):
        time_now = dt.now()
        procs_to_remove_from_lines = self.env['procurement.order']
        for order_id in dict_procs_lines.keys():
            for pol_id in dict_procs_lines[order_id].keys():
                pol = self.env['purchase.order.line'].search([('id', '=', pol_id)])
                procurement_ids = dict_procs_lines[order_id][pol_id]
                for proc in pol.procurement_ids:
                    if proc.id not in procurement_ids:
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
                pol = self.env['purchase.order.line'].search([('id', '=', pol_id)])
                if not pol:
                    continue
                procurements = self.search([('id', 'in', dict_procs_lines[order_id][pol_id])])
                for proc in procurements:
                    if proc not in pol.procurement_ids:
                        proc.add_proc_to_line(pol)
        return u"\nAdding procs into running lines and adjusting moves no procs qty for running " \
               u"lines: %s s." % int((dt.now() - time_now).seconds)

    @api.model
    def launch_procurement_redistribution(self, dict_procs_lines, return_msg, jobify=False):
        redistribute_procurements_in_separate_jobs = bool(self.env['ir.config_parameter'].
                                                          get_param(
            'purchase_procurement_just_in_time.redistribute_procurements_in_separate_jobs'))
        if len(dict_procs_lines.keys()) > 1 and jobify and redistribute_procurements_in_separate_jobs:
            time_now = dt.now()
            total_number_orders = len(dict_procs_lines.keys())
            number_order = 0
            for order_id in dict_procs_lines.keys():
                order = self.env['purchase.order'].search([('id', '=', order_id)])
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
    def set_exception_for_procs(self, msg=''):
        if not msg:
            msg = _("There is no supplier associated to product")
        procs_to_set_to_exception = self.search([('id', 'in', self.ids), ('state', '!=', 'exception')])
        procs_to_set_to_exception.write({'state': 'exception'})
        for proc in procs_to_set_to_exception:
            proc.with_context(message_code='delete_when_proc_no_exception').message_post(msg)

    @api.multi
    def make_po(self):
        res = {}
        for proc in self:
            if not self.env['procurement.order']._get_product_supplier(proc):
                proc.set_exception_for_procs()
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
        pol = procurement.purchase_line_id
        if pol.order_id.shipped or pol and procurement.forced_to_done_by_reception:
            return True
        return super(ProcurementOrderPurchaseJustInTime, self)._check(procurement)

    @api.model
    def unlink_useless_messages(self):
        self.env.cr.execute("""WITH message_ids_to_delete AS (
    SELECT mm.id AS message_id
    FROM mail_message mm
      LEFT JOIN procurement_order po ON po.id = mm.res_id
    WHERE mm.model = 'procurement.order' AND po.state NOT IN ('exception', 'buy_to_run')
          AND mm.code = 'delete_when_proc_no_exception')

DELETE FROM mail_message mm
WHERE exists(SELECT message_id
             FROM message_ids_to_delete
             WHERE message_id = mm.id)""")
