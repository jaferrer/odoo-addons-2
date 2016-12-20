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


@job
def job_purchase_schedule(session, model_name, compute_all_products, compute_supplier_ids,
                          compute_product_ids, jobify, context=None):
    model_instance = session.pool[model_name]
    handler = ConnectorSessionHandler(session.cr.dbname, session.uid, session.context)
    with handler.session() as session:
        result = model_instance.launch_purchase_schedule(session.cr, session.uid, compute_all_products,
                                                         compute_supplier_ids, compute_product_ids, jobify,
                                                         context=context)
    return result


@job
def job_purchase_schedule_procurements(session, model_name, ids, context=None):
    model_instance = session.pool[model_name]
    handler = ConnectorSessionHandler(session.cr.dbname, session.uid, session.context)
    with handler.session() as session:
        result = model_instance.purchase_schedule_procurements(session.cr, session.uid, ids, context=context)
    return result


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
    def remove_done_moves(self):
        """Splits the given procs creating a copy with the qty of their done moves and set to done.
        """
        for procurement in self:
            if procurement.rule_id.action == 'buy':
                qty_done_product_uom = sum([m.product_qty for m in procurement.move_ids if m.state == 'done'])
                qty_done_proc_uom = self.env['product.uom']._compute_qty(procurement.product_id.uom_id.id,
                                                                         qty_done_product_uom,
                                                                         procurement.product_uom.id)
                if float_compare(qty_done_proc_uom, 0.0, precision_rounding=procurement.product_uom.rounding) > 0:
                    remaining_qty = procurement.product_qty - qty_done_proc_uom
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
                                        description=_("Scheduling purchase orders"), context=self.env.context)
        else:
            self.launch_purchase_schedule(compute_all_products, compute_supplier_ids, compute_product_ids,
                                          jobify)

    @api.model
    def launch_purchase_schedule(self, compute_all_products, compute_supplier_ids, compute_product_ids, jobify):
        domain_procurements_to_run = [('state', 'not in', ['cancel', 'done', 'exception']),
                                      ('rule_id.action', '=', 'buy'),
                                      ('product_id.seller_id', '!=', False)]
        if not compute_all_products and compute_product_ids:
            domain_procurements_to_run += [('product_id', 'in', compute_product_ids)]
        procurements_to_tun = self.search(domain_procurements_to_run)
        ignore_past_procurements = bool(self.env['ir.config_parameter'].
                                        get_param('purchase_procurement_just_in_time.ignore_past_procurements'))
        dict_procs_suppliers = {}
        while procurements_to_tun:
            seller = self._get_product_supplier(procurements_to_tun[0])
            company = procurements_to_tun[0].company_id
            product = procurements_to_tun[0].product_id
            location = procurements_to_tun[0].location_id
            domain = [('id', 'in', procurements_to_tun.ids),
                      ('company_id', '=', company.id),
                      ('product_id', '=', product.id),
                      ('location_id', '=', location.id)]
            if ignore_past_procurements:
                suppliers = product.seller_ids and self.env['product.supplierinfo']. \
                    search([('id', 'in', product.seller_ids.ids),
                            ('name', '=', product.seller_id.id)]) or False
                if suppliers:
                    min_date = fields.Datetime.to_string(seller.schedule_working_days(product.seller_delay, dt.now()))
                else:
                    min_date = fields.Datetime.now()
                past_procurements = self.search(domain + [('date_planned', '<=', min_date)])
                if past_procurements:
                    procurements_to_tun -= past_procurements
                    past_procurements.remove_procs_from_lines(unlink_moves_to_procs=True)
                domain += [('date_planned', '>', min_date)]
            procurements = self.search(domain)
            if dict_procs_suppliers.get(seller):
                dict_procs_suppliers[seller] += procurements
            else:
                dict_procs_suppliers[seller] = procurements
            procurements_to_tun -= procurements
        for seller in dict_procs_suppliers.keys():
            if dict_procs_suppliers[seller] and \
                    (compute_all_products or not compute_supplier_ids or
                     compute_supplier_ids and seller.id in compute_supplier_ids):
                if jobify:
                    session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
                    job_purchase_schedule_procurements. \
                        delay(session, 'procurement.order', dict_procs_suppliers[seller].ids,
                              description=_("Scheduling purchase orders for seller %s and location %s") %
                              (seller.display_name, location.display_name), context=self.env.context)
                else:
                    dict_procs_suppliers[seller].purchase_schedule_procurements()

    @api.multi
    def compute_procs_for_first_line_found(self, purchase_lines, dict_procs_lines):
        pol = purchase_lines[0]
        procs_for_first_line = self.env['procurement.order'].search([('purchase_line_id', '=', pol.id),
                                                                     ('state', 'in', ['done', 'cancel'])])
        remaining_qty = pol.remaining_qty
        procurements = self
        for proc in procurements:
            proc_qty_pol_uom = self.env['product.uom']. \
                _compute_qty(proc.product_uom.id, proc.product_qty, pol.product_uom.id)
            if float_compare(remaining_qty, proc_qty_pol_uom,
                             precision_rounding=pol.product_uom.rounding) >= 0:
                procs_for_first_line |= proc
                remaining_qty -= proc_qty_pol_uom
            else:
                break
        if not dict_procs_lines.get(pol):
            dict_procs_lines[pol] = procs_for_first_line
        else:
            dict_procs_lines[pol] |= procs_for_first_line
        if procs_for_first_line:
            procurements -= procs_for_first_line
        purchase_lines = purchase_lines[1:]
        return procurements, purchase_lines, dict_procs_lines

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
                    search([('order_id.state', 'not in', ['draft', 'done', 'cancel']),
                            ('order_id.location_id', '=', rec.location_id.id),
                            ('product_id', '=', rec.product_id.id),
                            ('remaining_qty', '>', 0)], order='date_planned asc, remaining_qty desc')
                while procurements and purchase_lines:
                    procurements, purchase_lines, dict_procs_lines = procurements. \
                        compute_procs_for_first_line_found(purchase_lines, dict_procs_lines)
                # If some procurements are not assigned yet, we check draft lines
                purchase_lines = procurements and self.env['purchase.order.line']. \
                    search([('order_id.state', '=', 'draft'),
                            ('order_id.location_id', '=', rec.location_id.id),
                            ('product_id', '=', rec.product_id.id),
                            ('remaining_qty', '>', 0)], order='date_planned asc, remaining_qty desc') or False
                while procurements and purchase_lines:
                    purchase_lines = self.env['purchase.order.line']. \
                        search([('order_id.state', '=', 'draft'),
                                ('order_id.location_id', '=', rec.location_id.id),
                                ('product_id', '=', rec.product_id.id),
                                ('remaining_qty', '>', 0)], order='date_planned asc, remaining_qty desc')
                    procurements, purchase_lines, dict_procs_lines = procurements. \
                        compute_procs_for_first_line_found(purchase_lines, dict_procs_lines)
                list_products_done += [(rec.product_id, rec.location_id)]
                not_assigned_procs |= procurements
        return dict_procs_lines, not_assigned_procs

    @api.model
    def get_purchase_line_procurements(self, first_proc, seller, order_by, force_domain=None):
        """Returns procurements that must be integrated in the same purchase order line as first_proc, by
        taking all procurements of the same product as first_proc between the date of first proc and date_end.
        """
        frame = seller.order_group_period
        date_end = False
        if frame and frame.period_type:
            date_end = fields.Datetime.to_string(
                frame.get_date_end_period(fields.Datetime.from_string(first_proc.date_planned))
            )
        domain_procurements = [('product_id', '=', first_proc.product_id.id),
                               ('location_id', '=', first_proc.location_id.id),
                               ('company_id', '=', first_proc.company_id.id),
                               ('date_planned', '>=', first_proc.date_planned)] + (force_domain or [])
        if first_proc.rule_id.picking_type_id:
            domain_procurements += [('rule_id.picking_type_id', '=', first_proc.rule_id.picking_type_id.id)]
        domain_max_date = date_end and [('date_planned', '<', date_end)] or []
        procurements_grouping_period = self.search(domain_procurements + domain_max_date, order=order_by)
        line_qty_product_uom = sum([self.env['product.uom'].
                                   _compute_qty(proc.product_uom.id, proc.product_qty,
                                                proc.product_id.uom_id.id) for proc in procurements_grouping_period])
        suppliers = first_proc.product_id.seller_ids. \
            filtered(lambda supplier: supplier.name == self._get_product_supplier(first_proc))
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
        domain_date_not_defined = ['|', ('date_order', '=', False), ('date_order_max', '=', False)]
        available_draft_po_ids = self.env['purchase.order'].search(main_domain + domain_date_defined)
        draft_order = False
        if available_draft_po_ids:
            return available_draft_po_ids[0]
        frame = seller.order_group_period
        date_ref = seller.schedule_working_days(days_delta, dt.today())
        if frame and frame.period_type:
            date_order, date_order_max = frame.get_start_end_dates(purchase_date, date_ref=date_ref)
        else:
            date_order = dt.now()
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
        if not draft_order and not seller.nb_max_draft_orders or seller.nb_draft_orders < seller.nb_max_draft_orders:
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
    def create_draft_lines(self):
        days_delta = int(self.env['ir.config_parameter'].
                         get_param('purchase_procurement_just_in_time.delta_begin_grouping_period') or 0)
        if self:
            company = self[0].company_id
            order_by = 'date_planned asc, product_qty asc, id asc'
            # Let's process procurements by grouping period
            procurements = self.search([('id', 'in', self.ids)], order=order_by)
            seller = self._get_product_supplier(procurements[0])
            while procurements:
                first_proc = procurements[0]
                product = first_proc.product_id
                pol_procurements = self.get_purchase_line_procurements(
                    first_proc, seller, order_by,
                    force_domain=[('id', 'in', procurements.ids), ('product_id', '=', product.id)]
                )
                schedule_date = self._get_purchase_schedule_date(first_proc, company)
                purchase_date = self._get_purchase_order_date(first_proc, company, schedule_date)
                # We consider procurements after the reference date
                # (if we ignore past procurements, past ones are already removed)
                date_ref = seller.schedule_working_days(days_delta, dt.today())
                purchase_date = max(purchase_date, date_ref)
                line_vals = self._get_po_line_values_from_proc(first_proc, seller, company, schedule_date)
                draft_order = first_proc.get_corresponding_draft_order(seller, purchase_date)
                if draft_order:
                    line_vals.update(order_id=draft_order.id)
                    line = self.env['purchase.order.line'].sudo().create(line_vals)
                    first_proc.add_proc_to_line(line)
                    for proc in pol_procurements:
                        if proc != first_proc:
                            new_qty, new_price = self._calc_new_qty_price(proc, po_line=line)
                            if new_qty > line.product_qty:
                                line.sudo().write({'product_qty': new_qty, 'price_unit': new_price})
                            proc.add_proc_to_line(line)
                procurements -= pol_procurements
            return procurements
        return self

    @api.multi
    def sanitize_draft_orders(self):
        seller = self._get_product_supplier(self[0])
        orders = self.env['purchase.order'].search([('state', '=', 'draft'),
                                                    ('partner_id', '=', seller.id)], order='date_order')
        order_lines = self.env['purchase.order.line'].search([('order_id', 'in', orders.ids)])
        procurements = self.env['procurement.order'].search([('purchase_line_id.order_id', 'in', orders.ids)])
        procurements.remove_procs_from_lines()
        order_lines.unlink()
        orders.write({
            'date_order': False,
            'date_order_max': False,
        })

    @api.multi
    def delete_useless_draft_orders(self):
        seller = self._get_product_supplier(self[0])
        orders = self.env['purchase.order'].search([('state', '=', 'draft'),
                                                    ('partner_id', '=', seller.id)])
        orders_to_unlink = self.env['purchase.order']
        for order in orders:
            if not order.order_line:
                orders_to_unlink |= order
        orders_to_unlink.unlink()

    @api.multi
    def purchase_schedule_procurements(self):
        sellers = {self._get_product_supplier(proc) for proc in self}
        assert len(sellers) == 1, "purchase_schedule_procurements should be called with procs of the same supplier"
        self.sanitize_draft_orders()
        dict_procs_lines, not_assigned_procs = self.compute_which_procs_for_lines()
        not_assigned_procs = not_assigned_procs.create_draft_lines()
        not_assigned_procs.remove_procs_from_lines(unlink_moves_to_procs=True)
        # TODO: mettre à jour les message ops
        self.env['procurement.order'].redistribute_procurements_in_lines(dict_procs_lines)
        self.delete_useless_draft_orders()

    @api.multi
    def remove_procs_from_lines(self, unlink_moves_to_procs=False):
        self.remove_done_moves()
        self.with_context(tracking_disable=True).write({'purchase_line_id': False})
        to_reset = self.search([('id', 'in', self.ids), ('state', 'in', ['running', 'exception'])])
        to_reset.with_context(tracking_disable=True).write({'state': 'buy_to_run'})
        for proc in self:
            if proc.state in ['done', 'cancel']:
                # Done and cancel procs should not change purchase order line
                continue
            proc_moves = self.env['stock.move'].search([('procurement_id', '=', proc.id),
                                                        ('state', 'not in', ['cancel', 'done'])]
                                                       ).with_context(mail_notrack=True)
            if unlink_moves_to_procs:
                proc_moves.with_context(cancel_procurement=True, mail_notrack=True).action_cancel()
                proc_moves.unlink()
            else:
                proc_moves.write({'purchase_line_id': False,
                                  'picking_id': False})

    @api.multi
    def add_proc_to_line(self, pol):
        pol.ensure_one()
        for rec in self:
            assert rec.state not in ['done', 'cancel']

            orig_pol = rec.purchase_line_id
            if orig_pol:
                rec.remove_procs_from_lines()
            orig_pol.adjust_move_no_proc_qty()

            rec.with_context(tracking_disable=True).write({'purchase_line_id': pol.id})
            if not rec.move_ids:
                continue

            running_moves = self.env['stock.move'].search([('id', 'in', rec.move_ids.ids),
                                                           ('state', 'not in', ['draft', 'done', 'cancel'])]
                                                          ).with_context(mail_notrack=True)
            if pol.state not in ['draft', 'done', 'cancel']:
                group = self.env['procurement.group'].search([('name', '=', pol.order_id.name),
                                                              ('partner_id', '=', pol.order_id.partner_id.id)], limit=1)
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
    def redistribute_procurements_in_lines(self, dict_procs_lines):
        for pol in dict_procs_lines.keys():
            procurements = dict_procs_lines[pol]
            for proc in pol.procurement_ids:
                if proc not in procurements:
                    proc.remove_procs_from_lines()
            for proc in procurements:
                if proc not in pol.procurement_ids:
                    proc.add_proc_to_line(pol)
            pol.adjust_move_no_proc_qty()

    @api.multi
    def make_po(self):
        res = {}
        for proc in self:
            if not self._get_product_supplier(proc):
                proc.message_post(_('There is no supplier associated to product %s') % (proc.product_id.name))
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
                return all(move.state in ['done', 'cancel'] for move in procurement.move_ids)
        return super(ProcurementOrderPurchaseJustInTime, self)._check(procurement)
