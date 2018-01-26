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

from openerp import models, fields, api, _
from openerp.tools.float_utils import float_compare, float_round
from openerp.addons.connector.exception import RetryableJobError


@job(default_channel='root.purchase_scheduler')
def job_purchase_schedule(session, model_name, compute_all_products, compute_supplier_ids,
                          compute_product_ids, jobify):
    result = session.env[model_name].launch_purchase_schedule(compute_all_products,
                                                              compute_supplier_ids,
                                                              compute_product_ids,
                                                              jobify)
    return result


@job(default_channel='root.purchase_scheduler')
def job_purchase_schedule_seller(session, model_name, seller_id, procurement_ids, jobify):
    result = session.env[model_name].launch_purchase_schedule_seller(seller_id, procurement_ids, jobify)
    return result


@job(default_channel='root.purchase_scheduler')
def job_purchase_schedule_procurements(session, model_name, ids, jobify):
    result = session.env[model_name].search([('id', 'in', ids)]).purchase_schedule_procurements(jobify)
    return result


@job(default_channel='root.purchase_scheduler_slave')
def job_create_draft_lines(session, model_name, dict_lines_to_create):
    result = session.env[model_name].create_draft_lines(dict_lines_to_create)
    return result


@job(default_channel='root.purchase_scheduler_slave')
def job_redistribute_procurements_in_lines(session, model_name, dict_procs_lines):
    result = session.env[model_name].redistribute_procurements_in_lines(dict_procs_lines)
    return result


@job(default_channel='root.purchase_scheduler_slave')
def job_sanitize_draft_orders(session, model_name, seller_id):
    result = session.env[model_name].sanitize_draft_orders(seller_id)
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
    date_buy_to_run = fields.Datetime(string=u"Date buy to run", copy=False, readonly=True)

    @api.multi
    def write(self, vals):
        if vals.get('state') == 'buy_to_run':
            vals['date_buy_to_run'] = fields.Datetime.now()
        return super(ProcurementOrderPurchaseJustInTime, self).write(vals)

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
                          jobify=True, manual=False):
        config_sellers_manually = bool(self.env['ir.config_parameter'].
                                       get_param('purchase_procurement_just_in_time.config_sellers_manually'))
        if manual or not config_sellers_manually:
            compute_supplier_ids = compute_supplier_ids and compute_supplier_ids.ids or []
            compute_product_ids = compute_product_ids and compute_product_ids.ids or []
            session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
            if jobify:
                job_purchase_schedule.delay(session, 'procurement.order', compute_all_products,
                                            compute_supplier_ids, compute_product_ids, jobify,
                                            description=_("Scheduling purchase orders"))
            else:
                job_purchase_schedule(session, 'procurement.order', compute_all_products,
                                      compute_supplier_ids, compute_product_ids, jobify)

    @api.model
    def launch_purchase_schedule(self, compute_all_products, compute_supplier_ids, compute_product_ids, jobify):
        self.env['product.template'].update_seller_ids()
        stock_scheduler_controller_line = self.env['stock.scheduler.controller'].search([('done', '=', False)], limit=1)
        if stock_scheduler_controller_line:
            raise RetryableJobError(u"Impossible to launch purchase scheduler when stock scheduler is running",
                                    seconds=1200)
        if not compute_supplier_ids:
            active_sellers = self.env['product.supplierinfo'].read_group([('product_tmpl_id.active', '=', True)],
                                                                         ['name'], ['name'])
            compute_supplier_ids = [item['name'][0] for item in active_sellers]
        for seller_id in compute_supplier_ids:
            query = """WITH po_to_process AS (
    SELECT po.id
    FROM procurement_order po
      LEFT JOIN product_product pp ON pp.id = po.product_id
      LEFT JOIN procurement_rule pr ON pr.id = po.rule_id
    WHERE po.state NOT IN ('cancel', 'done', 'exception') AND pr.action = 'buy'),

    min_ps_sequences AS (
      SELECT
        po.id            AS procurement_order_id,
        min(ps.sequence) AS min_ps_sequence
      FROM procurement_order po
        LEFT JOIN product_product pp ON pp.id = po.product_id
        LEFT JOIN product_supplierinfo ps ON ps.product_tmpl_id = pp.product_tmpl_id
      WHERE po.id IN (SELECT po_to_process.id
                      FROM po_to_process) AND
            (ps.company_id = po.company_id OR ps.company_id IS NULL)
      GROUP BY po.id),

    min_ps_sequences_and_id AS (
      SELECT
        po.id      AS procurement_order_id,
        mps.min_ps_sequence,
        min(ps.id) AS min_ps_id_for_sequence
      FROM procurement_order po
        LEFT JOIN product_product pp ON pp.id = po.product_id
        LEFT JOIN product_supplierinfo ps ON ps.product_tmpl_id = pp.product_tmpl_id
        LEFT JOIN min_ps_sequences mps ON mps.procurement_order_id = po.id
      WHERE po.id IN (SELECT po_to_process.id
                      FROM po_to_process) AND
            (ps.company_id = po.company_id OR ps.company_id IS NULL) AND
            ps.sequence = mps.min_ps_sequence
      GROUP BY po.id, mps.min_ps_sequence),

    result AS (
      SELECT
        po.id                   AS procurement_order_id,
        (CASE WHEN ps.name IS NOT NULL
          THEN ps.name
         ELSE pp.seller_id END) AS seller_id,
        po.company_id,
        po.location_id,
        po.product_id
      FROM procurement_order po
        LEFT JOIN product_product pp ON pp.id = po.product_id
        LEFT JOIN product_supplierinfo ps ON ps.product_tmpl_id = pp.product_tmpl_id
        LEFT JOIN min_ps_sequences_and_id mps ON mps.procurement_order_id = po.id
      WHERE po.id IN (SELECT po_to_process.id
                      FROM po_to_process) AND
            (ps.company_id = po.company_id OR ps.company_id IS NULL) AND
            ps.sequence = mps.min_ps_sequence AND
            ps.id = mps.min_ps_id_for_sequence)

SELECT *
FROM result
WHERE seller_id = %s""" % seller_id
            arguments_needed = False
            if not compute_all_products and compute_product_ids:
                query += """ AND product_id in %s"""
                arguments_needed = True
            if arguments_needed:
                self.env.cr.execute(query, (tuple(compute_product_ids),))
            else:
                self.env.cr.execute(query)
            procurement_for_seller_ids = [item[0] for item in self.env.cr.fetchall()]
            session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
            supplier = self.env['res.partner'].search([('id', '=', seller_id)])
            if not procurement_for_seller_ids:
                if jobify:
                    job_sanitize_draft_orders.delay(session, 'procurement.order', seller_id,
                                                    description=_("Deleting draft orders for supplier %s" % supplier.display_name))
                else:
                    job_sanitize_draft_orders(session, 'procurement.order', seller_id)
            elif jobify:
                job_purchase_schedule_seller.delay(session, 'procurement.order', seller_id, procurement_for_seller_ids,
                                                   jobify, description=_("Scheduling purchase orders for supplier %s" %
                                                                         supplier.display_name))
            else:
                job_purchase_schedule_seller(session, 'procurement.order', seller_id, procurement_for_seller_ids,
                                             jobify)

    @api.model
    def get_delivery_date_for_today_order(self, product, seller):
        suppliers = product.seller_ids and self.env['product.supplierinfo']. \
            search([('id', 'in', product.seller_ids.ids),
                    ('name', '=', seller.id)]) or False
        if suppliers:
            min_date = fields.Datetime.to_string(seller.schedule_working_days(product.seller_delay, dt.now()))
        else:
            min_date = fields.Datetime.now()
        return min_date

    @api.model
    def sanitize_draft_orders(self, seller_id):
        orders = self.env['purchase.order'].search([('state', '=', 'draft'), ('partner_id', '=', seller_id)])
        procurements = self.env['procurement.order'].search([('purchase_line_id.order_id', 'in', orders.ids)])
        procurements.remove_procs_from_lines()
        orders.unlink()
        self.env.invalidate_all()

    @api.model
    def launch_purchase_schedule_seller(self, seller_id, procurement_ids, jobify):
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
                min_date = self.get_delivery_date_for_today_order(product, seller)
                past_procurements = self.search(domain + [('date_planned', '<=', min_date)])
                if past_procurements:
                    past_procurements.remove_procs_from_lines(unlink_moves_to_procs=True)
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
                                  description=_("Scheduling purchase orders for seller %s, "
                                                "company %s and location %s") %
                                  (seller.display_name, company.display_name, location.display_name))
                    else:
                        job_purchase_schedule_procurements(session, 'procurement.order', procurements.ids, jobify)

    @api.multi
    def compute_procs_for_first_line_found(self, procurements, purchase_line_ids, dict_procs_lines):
        pol = self.env['purchase.order.line'].search([('id', '=', purchase_line_ids[0])])
        procs_for_first_line_ids = self.env['procurement.order'].search([('purchase_line_id', '=', pol.id),
                                                                         ('state', 'in', ['done', 'cancel'])]).ids
        remaining_qty = pol.remaining_qty
        for proc in procurements:
            proc_product = self.env['product.product'].search([('id', '=', proc['product_id'][0])])
            self.env.cr.execute("""SELECT COALESCE(sum(sm.product_qty), 0)
FROM stock_move sm
WHERE sm.state = 'done' AND sm.procurement_id = %s""", (proc['id'],))
            fetchall = self.env.cr.fetchall()
            done_moves_qty = fetchall and fetchall[0][0] or 0
            proc_qty_pol_uom = self.env['product.uom']._compute_qty(proc['product_uom'][0], proc['product_qty'],
                                                                    proc['product_uom'][0])
            done_moves_qty_pol_uom = self.env['product.uom']._compute_qty(proc_product.uom_id.id, done_moves_qty,
                                                                          pol.product_uom.id)
            remaining_proc_qty_pol_uom = proc_qty_pol_uom - done_moves_qty_pol_uom
            if float_compare(remaining_qty, remaining_proc_qty_pol_uom,
                             precision_rounding=pol.product_uom.rounding) >= 0:
                procs_for_first_line_ids += [proc['id']]
                remaining_qty -= remaining_proc_qty_pol_uom
            else:
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
    def compute_which_procs_for_lines(self, procurement_ids):
        forbidden_order_states = self.get_forbidden_order_states_for_proc_assignment()
        ORDER_BY_CLAUSE = """
ORDER BY pol.date_planned ASC, pol.remaining_qty DESC"""
        dict_procs_lines = {}
        not_assigned_proc_ids = []
        possible_domains = self.env['procurement.order']. \
            read_group(domain=[('id', 'in', procurement_ids)], fields=['company_id', 'location_id', 'product_id'],
                       groupby=['company_id', 'location_id', 'product_id'], lazy=False)
        for possible_domain in possible_domains:
            company_id = possible_domain['company_id'][0]
            location_id = possible_domain['location_id'][0]
            product_id = possible_domain['product_id'][0]
            ORDER_LINES_QUERY = """SELECT pol.id
            FROM purchase_order_line pol
              LEFT JOIN purchase_order po ON po.id = pol.order_id
            WHERE po.state NOT IN %s AND
                  coalesce(pol.remaining_qty, 0) > 0 AND
                  po.company_id = %s AND
                  po.location_id = %s AND
                  pol.product_id = %s""" % (tuple(forbidden_order_states), company_id, location_id, product_id)
            procurements = self.env['procurement.order'].search_read(fields=['product_id', 'location_id', 'product_qty', 'product_uom'],
                                                                     domain=[('id', 'in', procurement_ids),
                                                                             ('product_id', '=', product_id),
                                                                             ('company_id', '=', company_id),
                                                                             ('location_id', '=', location_id)],
                                                                     order='date_planned asc, product_qty asc')
            # First, let's check running lines
            self.env.cr.execute(ORDER_LINES_QUERY + """ AND po.state != 'draft'""" + ORDER_BY_CLAUSE)
            purchase_line_ids = [item[0] for item in self.env.cr.fetchall()]
            while procurements and purchase_line_ids:
                procurements, purchase_line_ids, dict_procs_lines = self. \
                    compute_procs_for_first_line_found(procurements, purchase_line_ids, dict_procs_lines)
            # If some procurements are not assigned yet, we check draft lines
            self.env.cr.execute(ORDER_LINES_QUERY + """ AND po.state = 'draft'""" + ORDER_BY_CLAUSE)
            purchase_line_ids = [item[0] for item in self.env.cr.fetchall()]
            while procurements and purchase_line_ids:
                procurements, purchase_line_ids, dict_procs_lines = self. \
                    compute_procs_for_first_line_found(procurements, purchase_line_ids, dict_procs_lines)
            not_assigned_proc_ids += [proc['id'] for proc in procurements]
        return dict_procs_lines, not_assigned_proc_ids

    @api.model
    def get_purchase_line_procurements(self, first_proc, purchase_date, company, seller, order_by, force_domain=None):
        """Returns procurements that must be integrated in the same purchase order line as first_proc, by
        taking all procurements of the same product as first_proc between the date of first proc and date_end.
        """
        procurements_grouping_period = self.env['procurement.order']
        frame = seller.get_effective_order_group_period()
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
        seller = self.env['procurement.order']._get_product_supplier(first_proc)
        supplierinfo = self.env['product.supplierinfo'].search([('id', 'in', first_proc.product_id.seller_ids.ids),
                                                                ('name', '=', seller and seller.id or False)],
                                                               order='sequence, id', limit=1)
        moq = supplierinfo and supplierinfo.min_qty or False
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
        }

    @api.multi
    def get_corresponding_draft_order(self, seller, purchase_date):
        # look for any other draft PO for the same supplier to attach the new line.
        # If no one is found, we create a new draft one
        self.ensure_one()
        force_creation = self.env.context.get('force_creation')
        forbid_creation = self.env.context.get('forbid_creation')
        days_delta = int(self.env['ir.config_parameter']. \
            get_param('purchase_procurement_just_in_time.delta_begin_grouping_period') or 0)
        draft_order = False
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
        allowed_creation = not seller.nb_max_draft_orders or seller.get_nb_draft_orders() < seller.nb_max_draft_orders
        if not draft_order and (allowed_creation or force_creation) and not forbid_creation:
            name = self.env['ir.sequence'].next_by_code('purchase.order') or _('PO: %s') % self.name
            po_vals = self.get_corresponding_draft_order_values(name, origin, seller, date_order, date_order_max)
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
        nb_draft_orders = 0
        while procurements_to_check:
            first_proc = procurements_to_check[0]
            company = first_proc.company_id
            product = first_proc.product_id
            # Let's process procurements by grouping period
            seller = self.env['procurement.order']._get_product_supplier(first_proc)
            schedule_date = self._get_purchase_schedule_date(first_proc, company)
            purchase_date = self._get_purchase_order_date(first_proc, company, schedule_date)
            pol_procurements = self. \
                get_purchase_line_procurements(first_proc, purchase_date, company, seller, order_by,
                                               force_domain=[('id', 'in', procurements_to_check.ids)])
            # We consider procurements after the reference date
            # (if we ignore past procurements, past ones are already removed)
            date_ref = seller.schedule_working_days(days_delta, dt.today())
            purchase_date = max(purchase_date, date_ref)
            line_vals = self._get_po_line_values_from_proc(first_proc, seller, company, schedule_date)
            forbid_creation = bool(seller.nb_max_draft_orders)
            draft_order = first_proc.with_context(forbid_creation=forbid_creation). \
                get_corresponding_draft_order(seller, purchase_date)
            if draft_order and pol_procurements:
                line_vals.update(order_id=draft_order.id, product_qty=0)
                if not dict_lines_to_create.get(draft_order.id):
                    nb_draft_orders += 1
                    dict_lines_to_create[draft_order.id] = {}
                if not dict_lines_to_create[draft_order.id].get(product.id):
                    dict_lines_to_create[draft_order.id][product.id] = {'vals': line_vals,
                                                                        'procurement_ids': pol_procurements.ids}
                else:
                    dict_lines_to_create[draft_order.id][product.id]['procurement_ids'] += pol_procurements.ids
                not_assigned_procs -= pol_procurements
            if seller.nb_max_draft_orders and seller.get_nb_draft_orders() >= seller.nb_max_draft_orders:
                procurements_to_check = self.search([('id', 'in', procurements_to_check.ids),
                                                     ('product_id', '!=', product.id)], order=order_by)
            else:
                procurements_to_check -= pol_procurements
        return not_assigned_procs, dict_lines_to_create

    @api.model
    def create_draft_lines(self, dict_lines_to_create):
        time_begin = dt.now()
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
        return _(u"Order was correctly filled in %s s." % int((dt.now() - time_begin).seconds))

    @api.model
    def launch_draft_lines_creation(self, dict_lines_to_create, return_msg, jobify=False):
        time_now = dt.now()
        fill_orders_in_separate_jobs = bool(self.env['ir.config_parameter'].
                                            get_param('purchase_procurement_just_in_time.fill_orders_in_separate_jobs'))

        if jobify and fill_orders_in_separate_jobs:
            total_number_orders = len(dict_lines_to_create.keys())
            number_order = 0
            for order_id in dict_lines_to_create.keys():
                order = self.env['purchase.order'].search([('id', '=', order_id)])
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
    def get_first_purchase_dates_for_seller(self, procurement_ids):
        possible_domains = self. \
            read_group(domain=[('id', 'in', procurement_ids)], fields=['company_id', 'location_id', 'product_id'],
                       groupby=['company_id', 'location_id', 'product_id'], lazy=False)
        first_purchase_dates = {}
        for possible_domain in possible_domains:
            company_id = possible_domain['company_id'][0]
            location_id = possible_domain['location_id'][0]
            product_id = possible_domain['product_id'][0]
            if company_id not in first_purchase_dates:
                first_purchase_dates[company_id] = {}
            if location_id not in first_purchase_dates[company_id]:
                first_purchase_dates[company_id][location_id] = {'first_purchase_date': False,
                                                                 'definitive': False,
                                                                 'procurement': self.env['procurement.order']}
            if first_purchase_dates[company_id][location_id]['definitive']:
                continue
            first_purchase_date = first_purchase_dates[company_id][location_id]['first_purchase_date']
            first_proc = self.search([('company_id', '=', company_id),
                                      ('location_id', '=', location_id),
                                      ('product_id', '=', product_id)], order='date_planned', limit=1)
            if not first_proc:
                continue
            company = self.env['res.company'].search([('id', '=', company_id)])
            schedule_date = self._get_purchase_schedule_date(first_proc, company)
            purchase_date = self._get_purchase_order_date(first_proc, company, schedule_date)
            if not purchase_date:
                continue
            if not first_purchase_date or first_purchase_date > purchase_date:
                first_purchase_dates[company_id][location_id]['first_purchase_date'] = purchase_date
                first_purchase_dates[company_id][location_id]['procurement'] = first_proc
            if first_purchase_date and first_purchase_date < dt.now():
                first_purchase_dates[company_id][location_id]['first_purchase_date'] = dt.now()
                first_purchase_dates[company_id][location_id]['procurement'] = first_proc
                first_purchase_dates[company_id][location_id]['definitive'] = True
        return first_purchase_dates

    @api.multi
    def create_nb_max_draft_orders(self, seller, first_purchase_date):
        self.ensure_one()
        nb_orders = 0
        ref_date = first_purchase_date
        while nb_orders < seller.nb_max_draft_orders:
            nb_orders += 1
            latest_order = self.with_context(force_creation=True). \
                get_corresponding_draft_order(seller, ref_date)
            assert latest_order, "Impossible to create draft purchase order for purchase date %s" % \
                fields.Datetime.to_string(ref_date)
            assert latest_order.date_order_max, "Impossible to determine end grouping period for start date %s" % \
                latest_order.date_order
            ref_date = fields.Datetime.from_string(latest_order.date_order_max) + timedelta(days=1)

    @api.multi
    def delete_useless_draft_orders(self, seller, company, location):
        seller.ensure_one()
        company.ensure_one()
        location.ensure_one()
        orders = self.env['purchase.order'].search([('state', '=', 'draft'),
                                                    ('partner_id', '=', seller.id),
                                                    ('date_order', '=', False),
                                                    ('company_id', '=', company.id),
                                                    ('location_id', '=', location.id)])
        orders_to_unlink = self.env['purchase.order']
        for order in orders:
            if not order.order_line:
                orders_to_unlink |= order
        orders_to_unlink.unlink()

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
    def check_procs_same_sellers(self):
        seller = self.env['res.partner']
        self.env.cr.execute("""SELECT
  min(id) AS proc_id
FROM procurement_order
WHERE id IN %s
GROUP BY company_id, product_id""", (tuple(self.ids),))
        fetchall = self.env.cr.fetchall()
        for key in fetchall:
            proc_id = key[0]
            proc = self.search([('id', '=', proc_id)])
            seller |= self.env['procurement.order']._get_product_supplier(proc)
        assert len(seller) == 1, "purchase_schedule_procurements should be called with procs of the same supplier"
        return seller

    @api.multi
    def purchase_schedule_procurements(self, jobify=False):
        return_msg = u""
        time_now = dt.now()
        company = self.check_procs_same_companies()
        location = self.check_procs_same_locations()
        seller = self.check_procs_same_sellers()
        return_msg += u"Checking same company, location and seller: %s s." % int((dt.now() - time_now).seconds)
        time_now = dt.now()
        dict_procs_lines, not_assigned_proc_ids = self.compute_which_procs_for_lines(self.ids)
        return_msg += u"\nComputing which procs for lines: %s s." % int((dt.now() - time_now).seconds)
        time_now = dt.now()
        if seller.nb_max_draft_orders and seller.get_effective_order_group_period():
            first_purchase_dates = self.get_first_purchase_dates_for_seller(not_assigned_proc_ids)
            for company_id in first_purchase_dates:
                for location_id in first_purchase_dates[company_id]:
                    first_purchase_date = first_purchase_dates[company_id][location_id]['first_purchase_date']
                    procurement = first_purchase_dates[company_id][location_id]['procurement']
                    procurement.create_nb_max_draft_orders(seller, first_purchase_date)
        return_msg += u"\nCreating draft orders if needed: %s s." % int((dt.now() - time_now).seconds)
        time_now = dt.now()
        not_assigned_procs = self.browse(not_assigned_proc_ids)
        not_assigned_procs, dict_lines_to_create = not_assigned_procs.group_procurements_by_orders()
        return_msg += u"\nGrouping unassigned procurements by orders: %s s." % int((dt.now() - time_now).seconds)
        time_now = dt.now()
        self.delete_useless_draft_orders(seller, company, location)
        return_msg += u"\nDeleting useless draft orders: %s s." % int((dt.now() - time_now).seconds)
        time_now = dt.now()
        if not_assigned_procs:
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
                procurements = self.search([('id', 'in', dict_procs_lines[order_id][pol_id])])
                for proc in procurements:
                    if proc not in pol.procurement_ids:
                        proc.add_proc_to_line(pol)
                if pol.order_id.state in self.env['purchase.order'].get_purchase_order_states_with_moves():
                    pol.adjust_move_no_proc_qty()
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
