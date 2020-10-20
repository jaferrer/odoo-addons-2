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

import logging
from datetime import datetime as dt

import openerp.addons.decimal_precision as dp
from dateutil.relativedelta import relativedelta
from openerp import fields, models, api, exceptions, _
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession
from openerp.tools import float_compare, float_round
from openerp.tools.sql import drop_view_if_exists

ORDERPOINT_CHUNK = 1
POP_PROCESS_CHUNK = 100

_logger = logging.getLogger(__name__)


class ForbiddenCancelProtectedProcurement(exceptions.except_orm):

    def __init__(self, proc_id):
        self.proc_id = proc_id
        super(ForbiddenCancelProtectedProcurement,
              self).__init__(_(u"Error!"), _(u"You can't cancel a protected procurement (ID=%s)") % proc_id)


@job(default_channel='root.procurement_just_in_time_chunk')
def pop_sub_process_orderpoints(session, model_name, ids):
    """Processes the given orderpoints."""
    _logger.info("<<Started chunk of %s pop computing orderpoints to process" % POP_PROCESS_CHUNK)
    controller_stock = session.env[model_name].search([('id', 'in', ids)])
    controller_stock.pop_job_orderpoint_process()


@job(default_channel='root.procurement_just_in_time')
def process_orderpoints(session, model_name, ids):
    """Processes the given orderpoints."""
    _logger.info("<<Started chunk of %s orderpoints to process" % ORDERPOINT_CHUNK)
    orderpoints = session.env[model_name].search([('id', 'in', ids)])
    orderpoints.process()
    job_uuid = session.context.get('job_uuid')
    if job_uuid:
        line = session.env['stock.scheduler.controller'].search([('job_uuid', '=', job_uuid), ('done', '=', False)])
        line.set_to_done()


@job(default_channel='root.auto_delete_cancelled_moves_procs')
def job_delete_cancelled_moves_and_procs(session, model_name, ids):
    objects_to_delete = session.env[model_name].search([('id', 'in', ids)])
    objects_to_delete.unlink()

@job(default_channel='root.auto_delete_cancelled_moves_procs')
def job_pop_delete_cancelled_moves_and_procs_jobs(session, model_name):
    session.env[model_name].delete_cancelled_moves_and_procs()

@job(default_channel='root.update_rsm_treat_by_scheduler')
def job_rsm_treat_by_scheduler(session, model_name, ids):
    objects_to_write = session.env[model_name].search([('id', 'in', ids)])
    objects_to_write.update_treat_by_scheduler_rsm(True)


@job(default_channel='root.update_rsm_treat_by_scheduler')
def job_rsm_not_treat_by_scheduler(session, model_name, ids):
    objects_to_write = session.env[model_name].search([('id', 'in', ids)])
    objects_to_write.update_treat_by_scheduler_rsm(False)


class StockLocationSchedulerSequence(models.Model):
    _name = 'stock.location.scheduler.sequence'
    _order = 'name,id'

    name = fields.Integer(string=u"Stock scheduler sequence", required=True)
    location_id = fields.Many2one('stock.location', string=u"Location", ondelete='cascade')
    exclude_non_manufactured_products = fields.Boolean(string=u"Exclude non-manufactured products",
                                                       help=u"If this option is checked, the scheduler whill process "
                                                            u"only products that can be manufactured in the location "
                                                            u"of the orderpoint.")
    exclude_manufactured_products = fields.Boolean(string=u"Exclude manufactured products",
                                                   help=u"If this option is checked, the scheduler whill process "
                                                        u"only products that can not be manufactured in the location "
                                                        u"of the orderpoint.")

    _sql_constraints = [
        ('location_sequence_unique', 'unique(location_id, name)',
         _(u"Each sequence must be unique for the same location!")),
    ]

    @api.model
    def cron_update_treat_by_scheduler_rsm(self):
        locations = self.search([]).mapped('location_id')
        rsm_treat_by_scheduler = self.env['stock.warehouse.orderpoint'].search([('location_id', 'in', locations.ids)])
        rsm_not_treat_by_scheduler = self.env['stock.warehouse.orderpoint'].search(
            [('location_id', 'not in', locations.ids)])

        if rsm_treat_by_scheduler:
            job_rsm_treat_by_scheduler.delay(ConnectorSession.from_env(self.env), 'stock.warehouse.orderpoint',
                                             rsm_treat_by_scheduler.ids,
                                             description=u"Update is treat by scheduler")

        if rsm_not_treat_by_scheduler:
            job_rsm_not_treat_by_scheduler.delay(ConnectorSession.from_env(self.env), 'stock.warehouse.orderpoint',
                                                 rsm_not_treat_by_scheduler.ids,
                                                 description=u"Update is not treat by scheduler")


class StockLocation(models.Model):
    _inherit = 'stock.location'

    stock_scheduler_sequence_ids = fields.One2many('stock.location.scheduler.sequence', 'location_id',
                                                   string=u"Stock scheduler sequence",
                                                   help=u"Same order as the logistic flow")


class StockLocationRoute(models.Model):
    _inherit = 'stock.location.route'

    stock_scheduler_sequence = fields.Integer(string=u"Stock scheduler sequence",
                                              help=u"Highest sequences will be processed first")


class StockMove(models.Model):
    _inherit = 'stock.move'

    to_delete = fields.Boolean(string=u"To delete", default=False, readonly=True, index=True)


class ProcurementOrderQuantity(models.Model):
    _inherit = 'procurement.order'

    qty = fields.Float(string="Quantity", digits_compute=dp.get_precision('Product Unit of Measure'),
                       help='Quantity in the default UoM of the product', compute="_compute_qty", store=True)
    protected_against_scheduler = fields.Boolean(u"Protected Against Scheduler", track_visibility='onchange')
    to_delete = fields.Boolean(string=u"To delete", default=False, readonly=True, index=True)

    @api.multi
    @api.depends('product_qty', 'product_uom')
    def _compute_qty(self):
        for m in self:
            qty = self.env['product.uom']._compute_qty_obj(m.product_uom, m.product_qty, m.product_id.uom_id)
            m.qty = qty

    @api.model
    def get_default_supplierinfos_for_orderpoint_confirm(self):
        return self.env['product.supplierinfo'].search([('name', 'in', self.env.context['compute_supplier_ids'])])

    @api.model
    def delete_old_controller_lines(self):
        keep_stock_controller_lines_for = bool(self.env['ir.config_parameter'].get_param(
            'stock_procurement_just_in_time.keep_stock_controller_lines_for', default=0))
        last_date_done = dt.now() - relativedelta(days=keep_stock_controller_lines_for)
        last_date_done = fields.Datetime.to_string(last_date_done)
        self.env.cr.execute("""DELETE FROM stock_scheduler_controller WHERE done IS TRUE AND date_done < %s""",
                            (last_date_done,))

    @api.model
    def insert_new_controller_lines(self, orderpoints, company_id):
        self.env.cr.execute("""INSERT INTO stock_scheduler_controller
(orderpoint_id,
 product_id,
 location_id,
 location_sequence,
 run_procs,
 done,
 create_date,
 write_date,
 create_uid,
 write_uid,
 company_id)

WITH user_id AS (SELECT %s AS user_id),

     company_id AS (SELECT %s AS company_id),

     manufactured_products AS (
       SELECT pp.id AS product_id,
              pr.location_id,
              TRUE  AS is_manufactured_product
       FROM product_product pp
              INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id AND coalesce(pt.active, FALSE) IS TRUE
              INNER JOIN stock_location_route_categ rel ON rel.categ_id = pt.categ_id
              INNER JOIN stock_location_route route ON route.id = rel.route_id AND coalesce(route.active, FALSE) IS TRUE
              INNER JOIN procurement_rule pr ON pr.route_id = route.id AND
                                                coalesce(pr.active, FALSE) IS TRUE AND pr.action = 'manufacture'
       WHERE coalesce(pp.active, FALSE) IS TRUE
       GROUP BY pp.id, pr.location_id

       UNION ALL

       SELECT pp.id AS product_id,
              pr.location_id,
              TRUE  AS is_manufactured_product
       FROM product_product pp
              INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id AND coalesce(pt.active, FALSE) IS TRUE
              INNER JOIN stock_route_product rel ON rel.product_id = pt.id
              INNER JOIN stock_location_route route ON route.id = rel.route_id AND coalesce(route.active, FALSE) IS TRUE
              INNER JOIN procurement_rule pr ON pr.route_id = route.id AND
                                                coalesce(pr.active, FALSE) IS TRUE AND pr.action = 'manufacture'
       WHERE coalesce(pp.active, FALSE) IS TRUE
       GROUP BY pp.id, pr.location_id),

     orderpoints_to_insert AS (
       SELECT op.id                             AS orderpoint_id,
              op.product_id,
              op.location_id,
              COALESCE(slss.name :: INTEGER, 0) AS location_sequence,
              FALSE                             AS run_procs,
              FALSE                             AS done,
              CURRENT_TIMESTAMP                 AS create_date,
              CURRENT_TIMESTAMP                 AS write_date,
              (SELECT user_id
               FROM user_id)                    AS create_uid,
              (SELECT user_id
               FROM user_id)                    AS write_uid
       FROM stock_warehouse_orderpoint op
              INNER JOIN stock_location_scheduler_sequence slss ON slss.location_id = op.location_id
              INNER JOIN product_product pp ON pp.id = op.product_id AND COALESCE(pp.active, FALSE) IS TRUE
              LEFT JOIN manufactured_products mpbl ON mpbl.product_id = op.product_id AND
                                                      mpbl.location_id = op.location_id
       WHERE op.id IN %s
         AND (COALESCE(slss.exclude_non_manufactured_products, FALSE) IS FALSE
         OR COALESCE(mpbl.is_manufactured_product, FALSE) IS TRUE)
         AND (COALESCE(slss.exclude_manufactured_products, FALSE) IS FALSE
         OR COALESCE(mpbl.is_manufactured_product, FALSE) IS FALSE)
       GROUP BY op.id, slss.name),

     list_sequences AS (
       SELECT location_sequence
       FROM orderpoints_to_insert
       GROUP BY location_sequence)

SELECT *,
       (SELECT company_id FROM company_id) AS company_id
FROM orderpoints_to_insert

UNION ALL

SELECT NULL                                AS orderpoint_id,
       NULL                                AS product_id,
       NULL                                AS location_id,
       location_sequence,
       TRUE                                AS run_procs,
       FALSE                               AS done,
       CURRENT_TIMESTAMP                   AS create_date,
       CURRENT_TIMESTAMP                   AS write_date,
       (SELECT user_id
        FROM user_id)                      AS create_uid,
       (SELECT user_id
        FROM user_id)                      AS write_uid,
       (SELECT company_id FROM company_id) AS company_id
FROM list_sequences""", (self.env.uid, company_id, tuple(orderpoints.ids + [0])))

    @api.model
    def _procure_orderpoint_confirm(self, use_new_cursor=False, company_id=False, run_procurements=True,
                                    run_moves=True, force_orderpoints=None):
        """
        Create procurement based on orderpoint

        :param bool use_new_cursor: if set, use a dedicated cursor and auto-commit after processing each procurement.
            This is appropriate for batch jobs only.
        """
        orderpoint_env = self.env['stock.warehouse.orderpoint']
        if force_orderpoints:
            orderpoints = force_orderpoints
        else:
            dom = company_id and [('company_id', '=', company_id)] or []
            if self.env.context.get('compute_product_ids') and not self.env.context.get('compute_all_products'):
                dom += [('product_id', 'in', self.env.context.get('compute_product_ids'))]
            if self.env.context.get('compute_supplier_ids') and not self.env.context.get('compute_all_products'):
                supplierinfos = self.get_default_supplierinfos_for_orderpoint_confirm()
                read_supplierinfos = supplierinfos.read(['id', 'product_tmpl_id'], load=False)
                dom += [('product_id.product_tmpl_id', 'in', [item['product_tmpl_id'] for item in read_supplierinfos])]
            orderpoints = orderpoint_env.search(dom)
        if run_procurements:
            self.env['procurement.order'].run_confirm_procurements(company_id=company_id)
        if run_moves:
            domain = company_id and [('company_id', '=', company_id)] or False
            self.env['procurement.order'].run_confirm_moves(domain)
        # we invalidate the already existing line of stock controller not yet started
        # done_date is kept to NULL, so we have a way to identify controller line invalidated
        if company_id:
            msg = "set to done before starting execution of Stock scheduler on {}".format(fields.Datetime.now())
            self.env.cr.execute("""UPDATE stock_scheduler_controller
    SET done= TRUE,
        job_uuid = %s
    WHERE coalesce(done, FALSE) IS FALSE
      AND job_uuid IS NULL
      AND company_id = %s;""", (msg, company_id,))
        self.delete_old_controller_lines()
        self.insert_new_controller_lines(orderpoints, company_id=company_id or self.env.user.company_id.id)
        return {}

    @api.multi
    def check_can_be_canceled(self, raise_error=True):
        for rec in self:
            if rec.protected_against_scheduler and self.env.context.get('is_scheduler') and not \
                    self.env.context.get('propagation_cancel'):
                if raise_error:
                    raise ForbiddenCancelProtectedProcurement(rec.id)
                else:
                    return False
        return True

    @api.multi
    def cancel(self):
        self.check_can_be_canceled()
        result = super(ProcurementOrderQuantity, self).cancel()
        if self.env.context.get('unlink_all_chain'):
            moves_to_unlink = self.env['stock.move']
            procurements_to_unlink = self.env['procurement.order']
            for rec in self:
                parent_moves = self.env['stock.move'].search([('procurement_id', '=', rec.id)])
                for move in parent_moves:
                    if move.state == 'cancel':
                        moves_to_unlink += move
                        if procurements_to_unlink not in procurements_to_unlink and move.procurement_id and \
                                move.procurement_id.state == 'cancel' and \
                                not any([move.state == 'done' for move in move.procurement_id.move_ids]):
                            procurements_to_unlink += move.procurement_id

            moves_to_unlink.write({'to_delete': True})
            procurements_to_unlink.write({'to_delete': True})

        return result

    @api.model
    def propagate_cancel(self, procurement):
        """
        Improves the original propagate_cancel, in order to cancel it even if one of its moves is done.
        """
        ignore_move_ids = []
        if procurement.rule_id.action == 'move':
            ignore_move_ids += self.env['stock.move'].search([('procurement_id', '=', procurement.id),
                                                              ('state', 'in', ['done', 'cancel'])]).ids
            # Keep proc with new qty if some moves are already done
            procurement.remove_done_moves()
        return super(ProcurementOrderQuantity,
                     self.sudo().with_context(ignore_move_ids=ignore_move_ids, propagation_cancel=True)).\
            propagate_cancel(procurement)

    @api.model
    def remove_done_moves(self):
        """Splits the given procs creating a copy with the qty of their done moves and set to done.
        """
        for procurement in self:
            if procurement.rule_id.action == 'move':
                qty_done = sum([move.product_qty for move in procurement.move_ids if move.state == 'done'])
                qty_done_proc_uom = self.env['product.uom']. \
                    _compute_qty_obj(procurement.product_id.uom_id, qty_done, procurement.product_uom)
                if procurement.product_uos:
                    qty_done_proc_uos = float_round(
                        self.env['product.uom']._compute_qty_obj(procurement.product_id.uom_id, qty_done,
                                                                 procurement.product_uos),
                        precision_rounding=procurement.product_uos.rounding
                    )
                else:
                    qty_done_proc_uos = float_round(qty_done_proc_uom,
                                                    precision_rounding=procurement.product_uom.rounding)
                if float_compare(qty_done, 0.0, precision_rounding=procurement.product_id.uom_id.rounding) > 0:
                    procurement.write({
                        'product_qty': float_round(qty_done_proc_uom,
                                                   precision_rounding=procurement.product_uom.rounding),
                        'product_uos_qty': qty_done_proc_uos,
                    })

    @api.multi
    def cancel_procs_just_in_time(self, stock_qty, qty):
        self.ensure_one()
        result = stock_qty
        try:
            with self.env.cr.savepoint():
                self.with_context(unlink_all_chain=True, cancel_procurement=True, is_scheduler=True).cancel()
                if self.state == 'cancel':
                    self.unlink()
                    result = stock_qty - qty
        except ForbiddenCancelProtectedProcurement as e:
            _logger.info(e.value)
        return result

    @api.model
    def pop_delete_cancelled_moves_and_procs_jobs(self):
        job = self.env['queue.job'].search([('state', 'not in', ['done', 'failed']),
                                            ('func_name', 'ilike', "%delete_cancelled_moves_and_procs%"),], limit=1)
        if job:
            return u"Job %s already in execution" % job.name
        job_pop_delete_cancelled_moves_and_procs_jobs.delay(ConnectorSession.from_env(self.env), 'procurement.order')

    @api.model
    def delete_cancelled_moves_and_procs(self, jobify=True):
        self.env.cr.execute("""SELECT id
FROM procurement_order
WHERE coalesce(to_delete, FALSE) IS TRUE""")
        procurement_to_delete_ids = [item[0] for item in self.env.cr.fetchall()]
        if jobify:
            while procurement_to_delete_ids:
                procurement_to_delete_id = procurement_to_delete_ids[0]
                procurement_to_delete_ids = procurement_to_delete_ids[1:]
                _logger.info(u"Poping job for procurement ID=%s (%s remaining)",
                             procurement_to_delete_id, len(procurement_to_delete_ids))
                job_delete_cancelled_moves_and_procs.delay(ConnectorSession.from_env(self.env),
                                                           'procurement.order', [procurement_to_delete_id])
                self.env.cr.commit()
        else:
            job_delete_cancelled_moves_and_procs(ConnectorSession.from_env(self.env),
                                                 'procurement.order', procurement_to_delete_ids)
        self.env.cr.execute("""SELECT id
FROM stock_move
WHERE coalesce(to_delete, FALSE) IS TRUE""")
        move_to_delete_ids = [item[0] for item in self.env.cr.fetchall()]
        if jobify:
            while move_to_delete_ids:
                move_to_delete_id = move_to_delete_ids[0]
                move_to_delete_ids = move_to_delete_ids[1:]
                _logger.info(u"Poping job for move ID=%s (%s remaining)",
                             move_to_delete_id, len(move_to_delete_ids))
                job_delete_cancelled_moves_and_procs.delay(ConnectorSession.from_env(self.env),
                                                           'stock.move', [move_to_delete_id])
                self.env.cr.commit()
        else:
            job_delete_cancelled_moves_and_procs(ConnectorSession.from_env(self.env),
                                                 'stock.move', move_to_delete_ids)


class StockMoveJustInTime(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def action_cancel(self):
        domain = [('id', 'in', self.ids),
                  ('id', 'not in', (self.env.context.get('ignore_move_ids') or []))]
        if self.env.context.get('do_not_try_to_cancel_done_moves'):
            domain += [('state', '!=', 'done')]
        moves_to_cancel = self.search(domain)
        return super(StockMoveJustInTime, moves_to_cancel).action_cancel()


class StockWarehouseOrderPointJit(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    stock_scheduler_sequence_ids = fields.One2many(string=u"Stock scheduler sequences",
                                                   related='location_id.stock_scheduler_sequence_ids')
    is_treat_by_scheduler = fields.Boolean(u"Treat by the scheduler", readonly=True, default=False)

    @api.multi
    def get_list_events(self):
        """Returns a dict of stock level requirements where the stock level is below minimum qty for the product and
        the location of the orderpoint."""
        self.ensure_one()
        events = self.compute_stock_levels_requirements(list_move_types=('in', 'planned', 'out', 'existing'),
                                                        limit=False, parameter_to_sort='date', to_reverse=False)
        return sorted(events, key=lambda event: event['date'])

    @api.multi
    def create_from_need(self, need, stock_after_event):
        """Creates a procurement to fulfill the given need with the data calculated from the given order point.
        Will set the date of the procurement at the date of the need.

        :param need: the 'stock levels requirements' dictionary to fulfill
        """
        proc = self.env['procurement.order']
        self.ensure_one()
        end_cover_date = fields.Datetime.from_string(need.get('date') or fields.Date.today()) + relativedelta(days=1)
        product_max_qty = self.get_max_qty(end_cover_date)
        if self.fill_strategy == 'duration':
            consider_end_contract_effect = bool(self.env['ir.config_parameter'].get_param(
                'stock_procurement_just_in_time.consider_end_contract_effect', default=False))
            if not consider_end_contract_effect:
                product_max_qty += self.product_min_qty
        qty = max(max(self.product_min_qty, product_max_qty) - stock_after_event, 0)
        if self.qty_multiple > 1:
            reste = qty % self.qty_multiple or 0.0
            if float_compare(reste, 0.0, precision_rounding=self.product_uom.rounding) > 0:
                qty += self.qty_multiple - reste
        qty = float_round(qty, precision_rounding=self.product_uom.rounding)

        if float_compare(qty, 0.0, precision_rounding=self.product_uom.rounding) > 0:
            proc_vals = proc._prepare_orderpoint_procurement(self, qty)
            if need['date']:
                proc_vals.update({'date_planned': need['date'] + ' 12:00:00'})
            proc = proc.create(proc_vals)
            if not self.env.context.get('procurement_no_run'):
                proc.run()
            _logger.debug("Created proc: %s, (%s, %s). Product: %s, Location: %s" %
                          (proc, proc.date_planned, proc.product_qty, self.product_id, self.location_id))
        else:
            _logger.debug("Requested qty is null, no procurement created")
        return proc

    @api.multi
    def get_last_scheduled_date(self):
        """Returns the last scheduled date for this order point."""
        self.ensure_one()
        last_schedule = self.compute_stock_levels_requirements(list_move_types=['in', 'out', 'existing'], limit=1,
                                                               parameter_to_sort='date', to_reverse=True)
        res = last_schedule and last_schedule[0].get('date') and \
            fields.Datetime.from_string(last_schedule[0].get('date')) or False
        return res

    @api.multi
    def remove_unecessary_procurements(self, timestamp):
        """Remove the unecessary procurements that are placed just before timestamp, and recreate one if necessary to
        match exactly this order point product_min_qty.

        :param timestamp: datetime object
        """
        for rec in self:
            # We get all running procurements placed after timestamp.
            procs = self.env['procurement.order'].search([('product_id', '=', rec.product_id.id),
                                                          ('location_id', '=', rec.location_id.id),
                                                          ('state', 'not in', ['done', 'cancel']),
                                                          ('date_planned', '>', fields.Datetime.to_string(timestamp))])
            if procs:
                _logger.debug("Removing not needed procurements: %s", procs.ids)
                procs.with_context(unlink_all_chain=True, cancel_procurement=True).cancel()
                procs.unlink()

    @api.multi
    def get_max_allowed_qty(self, date):
        self.ensure_one()
        product_max_qty = date and self.get_max_qty(fields.Datetime.from_string(date + ' 23:59:59')) or 0
        if self.fill_strategy == 'duration':
            consider_end_contract_effect = bool(self.env['ir.config_parameter'].get_param(
                'stock_procurement_just_in_time.consider_end_contract_effect', default=False))
            if not consider_end_contract_effect:
                product_max_qty += self.product_min_qty
        if self.qty_multiple > 1 and product_max_qty % self.qty_multiple != 0:
            product_max_qty = (product_max_qty // self.qty_multiple + 1) * self.qty_multiple
        relative_stock_delta = float(self.env['ir.config_parameter'].get_param(
            'stock_procurement_just_in_time.relative_stock_delta', default=0))
        absolute_stock_delta = float(self.env['ir.config_parameter'].get_param(
            'stock_procurement_just_in_time.absolute_stock_delta', default=0))
        return max((1 * float(relative_stock_delta) / 100) * product_max_qty, product_max_qty + absolute_stock_delta)

    @api.multi
    def is_over_stock_max(self, need, stock_after_event):
        self.ensure_one()
        max_qty = self.get_max_allowed_qty(need['date'])
        if float_compare(stock_after_event, max_qty, precision_rounding=self.product_id.uom_id.rounding) > 0:
            return True
        return False

    @api.multi
    def is_under_stock_min(self, stock_after_event):
        self.ensure_one()
        min_qty = self.product_min_qty
        if float_compare(stock_after_event, min_qty, precision_rounding=self.product_id.uom_id.rounding) < 0:
            return True
        return False

    @api.model
    def process_events_at_date(self, event, events, stock_after_event):
        self.ensure_one()
        events_at_date = [item for item in events if item['date'] == event['date']]
        stock_after_event += sum([item['move_qty'] for item in events_at_date])
        return events_at_date, stock_after_event

    @api.multi
    def process(self):
        """Process this orderpoint."""
        for op in self:
            _logger.debug("Computing orderpoint %s (%s, %s, %s)" % (op.id, op.name, op.product_id.display_name,
                                                                    op.location_id.display_name))
            events = op.get_list_events()
            done_dates = []
            events_at_date = []
            stock_after_event = 0
            for event in events:
                if event['date'] not in done_dates:
                    events_at_date, stock_after_event = op.process_events_at_date(event, events, stock_after_event)
                    done_dates += [event['date']]
                if op.is_over_stock_max(event, stock_after_event) and event['move_type'] in ['in', 'planned'] and event['proc_id']:
                    procs_oversupply = self.env['procurement.order']. \
                        search([('id', 'in', [item['proc_id'] for item in events_at_date]),
                                ('state', '!=', 'done')])
                    for proc_oversupply in procs_oversupply:
                        qty_same_proc = sum([item['move_qty']
                                            for item in events if item['proc_id'] == proc_oversupply.id])
                        _logger.debug("Oversupply detected: deleting procurements %s " % proc_oversupply.id)
                        stock_after_event = proc_oversupply.cancel_procs_just_in_time(stock_after_event, qty_same_proc)
                    if op.is_under_stock_min(stock_after_event) and \
                            any([item['move_type'] == 'out' for item in events_at_date]):
                        new_proc = op.create_from_need(event, stock_after_event)
                        stock_after_event += new_proc and new_proc.product_qty or 0
                elif op.is_under_stock_min(stock_after_event):
                    new_proc = op.create_from_need(event, stock_after_event)
                    stock_after_event += new_proc and new_proc.product_qty or 0
            # Now we want to make sure that at the end of the scheduled outgoing moves, the stock level is
            # the minimum quantity of the orderpoint.
            last_scheduled_date = op.get_last_scheduled_date()
            if last_scheduled_date:
                date_end = last_scheduled_date + relativedelta(days=1)
                op.remove_unecessary_procurements(date_end)

    @api.multi
    def process_from_screen(self):
        self.ensure_one()
        self.env['procurement.order'].sudo()._procure_orderpoint_confirm(use_new_cursor=False,
                                                                         company_id=False,
                                                                         run_procurements=False,
                                                                         run_moves=False,
                                                                         force_orderpoints=self)
        self.env['stock.scheduler.controller'].sudo().update_scheduler_controller()

    @api.model
    def get_query_move_in(self):
        return """SELECT sm.id,
       sm.product_qty,
       min(COALESCE(po.date_planned, sm.date))::DATE AS date,
       po.id
FROM stock_move sm
       LEFT JOIN stock_location sl ON sm.location_dest_id = sl.id
       LEFT JOIN procurement_order po ON sm.procurement_id = po.id
WHERE sm.product_id = %s
  AND sm.state NOT IN ('cancel', 'done', 'draft')
  AND sl.parent_left >= %s
  AND sl.parent_left < %s"""

    @api.model
    def get_query_moves_out(self):
        return """SELECT sm.id,
       sm.product_qty,
       min(sm.date)::DATE AS date
FROM stock_move sm
       LEFT JOIN stock_location sl ON sm.location_id = sl.id
WHERE sm.product_id = %s
  AND sm.state NOT IN ('cancel', 'done', 'draft')
  AND sl.parent_left >= %s
  AND sl.parent_left < %s"""

    @api.model
    def get_query_procs(self):
        return """SELECT po.id,
       min(po.date_planned)::DATE,
       min(po.qty)
FROM procurement_order po
       LEFT JOIN stock_location sl ON po.location_id = sl.id
       LEFT JOIN stock_move sm ON po.id = sm.procurement_id
WHERE po.product_id = %s
  AND sl.parent_left >= %s
  AND sl.parent_left < %s
  AND po.state NOT IN ('done', 'cancel')
  AND (sm.state = 'draft' OR sm.id IS NULL)"""

    @api.model
    def compute_stock_levels_requirements(self, list_move_types, limit=1, parameter_to_sort='date', to_reverse=False,
                                          max_date=None):
        """
        Computes stock level report
        :param product_id: int
        :param location: recordset
        :param list_move_types: tuple or list of strings (move types)
        :param limit: maximum number of lines in the result
        :param parameter_to_sort: str
        :param to_reverse: bool
        :return: list of need dictionaries
        """
        self.ensure_one()
        procurement_date_clause = max_date and " AND po.date_planned <= %s " or ""
        move_out_date_clause = max_date and " AND sm.date <= %s " or ""
        move_in_date_clause = max_date and " AND COALESCE(po.date_planned, sm.date) <= %s " or ""
        # Workaround for tests
        if not self.location_id.parent_left or not self.location_id.parent_right:
            self.env['stock.location']._parent_store_compute()
        params = (self.product_id.id, self.location_id.parent_left, self.location_id.parent_right)
        if max_date:
            params += (max_date,)

        # Computing the top parent location
        first_date = False
        result = []
        intermediate_result = []
        query_moves_in = self.get_query_move_in() + move_in_date_clause + """
GROUP BY sm.id, po.id, sm.product_qty
ORDER BY DATE"""
        self.env.cr.execute(query_moves_in, params)
        moves_in_tuples = self.env.cr.fetchall()

        query_moves_out = self.get_query_moves_out() + move_out_date_clause + """
GROUP BY sm.id, sm.product_qty
ORDER BY date"""
        self.env.cr.execute(query_moves_out, params)
        moves_out_tuples = self.env.cr.fetchall()

        stock_quant_restricted = self.env['stock.quant'].search([('product_id', '=', self.product_id.id),
                                                                 ('location_id', 'child_of', self.location_id.id)])
        query_procs = self.get_query_procs() + procurement_date_clause + """
GROUP BY po.id
ORDER BY po.date_planned"""
        self.env.cr.execute(query_procs, params)
        procurement_tuples = self.env.cr.fetchall()
        dates = []
        if moves_in_tuples:
            dates += [moves_in_tuples[0][2]]
        if moves_out_tuples:
            dates += [moves_out_tuples[0][2]]
        if procurement_tuples:
            dates += [procurement_tuples[0][1]]
        if dates:
            first_date = min(dates)

        # existing items
        existing_qty = self.location_id.usage in ['internal', 'transit'] and \
            sum([x.qty for x in stock_quant_restricted]) or 0
        intermediate_result += [{
            'proc_id': False,
            'location_id': self.location_id.id,
            'move_type': 'existing',
            'date': first_date,
            'move_qty': existing_qty,
            'move_id': False,
        }]
        # incoming items
        for sm in moves_in_tuples:
            intermediate_result += [{
                'proc_id': sm[3],
                'location_id': self.location_id.id,
                'move_type': 'in',
                'date': sm[2],
                'move_qty': sm[1],
                'move_id': sm[0],
            }]

        # outgoing items
        for sm in moves_out_tuples:
            intermediate_result += [{
                'proc_id': False,
                'location_id': self.location_id.id,
                'move_type': 'out',
                'date': sm[2],
                'move_qty': - sm[1],
                'move_id': sm[0],
            }]

        # planned items
        for po in procurement_tuples:
            intermediate_result += [{
                'proc_id': po[0],
                'location_id': self.location_id.id,
                'move_type': 'planned',
                'date': po[1],
                'move_qty': po[2],
                'move_id': False,
            }]

        intermediate_result = sorted(intermediate_result, key=lambda a: a['date'])
        qty = 0
        while intermediate_result:
            stock_levels = [item for item in intermediate_result if item['date'] == intermediate_result[0]['date']]
            total_qty = sum([item['move_qty'] for item in stock_levels])
            qty += total_qty
            for dictionary in stock_levels[:]:
                intermediate_result.remove(dictionary)
                if dictionary['move_type'] not in list_move_types:
                    continue
                level_qty = dictionary['move_qty']
                if dictionary['move_type'] != 'existing':
                    level_qty = qty
                result += [{
                    'proc_id': dictionary['proc_id'],
                    'product_id': self.product_id.id,
                    'location_id': dictionary['location_id'],
                    'move_type': dictionary['move_type'],
                    'date': dictionary['date'],
                    'qty': level_qty,
                    'move_qty': dictionary['move_qty'],
                    'move_id': dictionary['move_id'],
                }]
        result = sorted(result, key=lambda z: z[parameter_to_sort], reverse=to_reverse)
        if limit:
            return result[:limit]
        else:
            return result

    @api.multi
    def update_treat_by_scheduler_rsm(self, is_treat_by_scheduler):
        self.write({'is_treat_by_scheduler': is_treat_by_scheduler})


class StockLevelsReport(models.Model):
    _name = "stock.levels.report"
    _description = "Stock Levels Report"
    _order = "date"
    _auto = False

    id = fields.Integer("ID", readonly=True)
    product_id = fields.Many2one("product.product", string="Product", index=True)
    product_categ_id = fields.Many2one("product.category", string="Product Category")
    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse", index=True)
    other_warehouse_id = fields.Many2one("stock.warehouse", string="Origin/Destination")
    move_type = fields.Selection([('existing', 'Existing'), ('in', 'Incoming'), ('out', 'Outcoming')],
                                 string="Move Type", index=True)
    date = fields.Datetime("Date", index=True)
    qty = fields.Float("Stock Quantity", group_operator="last")
    move_qty = fields.Float("Moved Quantity")

    def init(self, cr):
        drop_view_if_exists(cr, "stock_levels_report")
        cr.execute("""CREATE OR REPLACE VIEW stock_levels_report AS (
    WITH
            link_location_warehouse AS (
                SELECT
                    sl.id AS location_id,
                    sw.id AS warehouse_id
                FROM stock_warehouse sw
                    LEFT JOIN stock_location sl_view ON sl_view.id = sw.view_location_id
                    LEFT JOIN stock_location sl ON sl.parent_left >= sl_view.parent_left AND
                                                   sl.parent_left <= sl_view.parent_right
        ),
            min_product AS (
                SELECT
                    min(sm.date_expected) - INTERVAL '1 second' AS min_date,
                    sm.product_id                               AS product_id
                FROM
                    stock_move sm
                    LEFT JOIN stock_location sl ON sm.location_dest_id = sl.id
                    LEFT JOIN link_location_warehouse link ON link.location_id = sm.location_id
                    LEFT JOIN link_location_warehouse link_dest ON link_dest.location_id = sm.location_dest_id
                WHERE ((link_dest.warehouse_id IS NOT NULL
                        AND (link.warehouse_id IS NULL OR link.warehouse_id != link_dest.warehouse_id))
                       OR (link.warehouse_id IS NOT NULL
                           AND (link_dest.warehouse_id IS NULL OR link.warehouse_id != link_dest.warehouse_id)))
                      AND sm.state :: TEXT <> 'cancel' :: TEXT
                      AND sm.state :: TEXT <> 'done' :: TEXT
                      AND sm.state :: TEXT <> 'draft' :: TEXT
                GROUP BY sm.product_id
        )

    SELECT
        foo.product_id :: TEXT || '-'
        || foo.warehouse_id :: TEXT || '-'
        || coalesce(foo.move_id :: TEXT, 'existing') AS id,
        foo.product_id,
        pt.categ_id                                  AS product_categ_id,
        foo.move_type,
        sum(foo.qty)
        OVER (PARTITION BY foo.warehouse_id, foo.product_id
            ORDER BY date)                           AS qty,
        foo.date                                     AS date,
        foo.qty                                      AS move_qty,
        foo.warehouse_id,
        foo.other_warehouse_id
    FROM
        (
            SELECT
                sq.product_id                               AS product_id,
                'existing' :: TEXT                          AS move_type,
                coalesce(min(mp.min_date), max(sq.in_date)) AS date,
                sum(sq.qty)                                 AS qty,
                NULL                                        AS move_id,
                link.warehouse_id,
                NULL                                        AS other_warehouse_id
            FROM
                stock_quant sq
                LEFT JOIN stock_location sl ON sq.location_id = sl.id
                LEFT JOIN link_location_warehouse link ON link.location_id = sl.location_id
                LEFT JOIN min_product mp ON mp.product_id = sq.product_id
            WHERE link.warehouse_id IS NOT NULL
            GROUP BY sq.product_id, link.warehouse_id

            UNION ALL

            SELECT
                sm.product_id     AS product_id,
                'in' :: TEXT      AS move_type,
                sm.date_expected  AS date,
                sm.product_qty    AS qty,
                sm.id             AS move_id,
                link_dest.warehouse_id,
                link.warehouse_id AS other_warehouse_id
            FROM
                stock_move sm
                LEFT JOIN stock_location sl ON sm.location_dest_id = sl.id
                LEFT JOIN link_location_warehouse link ON link.location_id = sm.location_id
                LEFT JOIN link_location_warehouse link_dest ON link_dest.location_id = sm.location_dest_id
            WHERE link_dest.warehouse_id IS NOT NULL
                  AND (link.warehouse_id IS NULL OR link.warehouse_id != link_dest.warehouse_id)
                  AND sm.state :: TEXT <> 'cancel' :: TEXT
                  AND sm.state :: TEXT <> 'done' :: TEXT
                  AND sm.state :: TEXT <> 'draft' :: TEXT

            UNION ALL

            SELECT
                sm.product_id          AS product_id,
                'out' :: TEXT          AS move_type,
                sm.date_expected       AS date,
                -sm.product_qty        AS qty,
                sm.id                  AS move_id,
                link.warehouse_id,
                link_dest.warehouse_id AS other_warehouse_id
            FROM
                stock_move sm
                LEFT JOIN stock_location sl ON sm.location_id = sl.id
                LEFT JOIN link_location_warehouse link ON link.location_id = sm.location_id
                LEFT JOIN link_location_warehouse link_dest ON link_dest.location_id = sm.location_dest_id
            WHERE link.warehouse_id IS NOT NULL
                  AND (link_dest.warehouse_id IS NULL OR link.warehouse_id != link_dest.warehouse_id)
                  AND sm.state :: TEXT <> 'cancel' :: TEXT
                  AND sm.state :: TEXT <> 'done' :: TEXT
                  AND sm.state :: TEXT <> 'draft' :: TEXT
        ) foo
        LEFT JOIN product_product pp ON foo.product_id = pp.id
        LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
)
        """)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def get_warehouse_for_stock_report(self):
        return self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1)

    @api.model
    def get_orderpoint_required_locations_ids(self):
        sequences = self.env['stock.location.scheduler.sequence'].search([])
        return [sequence.location_id.id for sequence in sequences]

    @api.multi
    def action_show_evolution(self):
        self.ensure_one()
        warehouse = self.get_warehouse_for_stock_report()
        if warehouse:
            ctx = dict(self.env.context)
            ctx.update({
                'search_default_warehouse_id': warehouse.id,
                'search_default_product_id': self.id,
            })
            return {
                'type': 'ir.actions.act_window',
                'name': _("Stock Evolution"),
                'res_model': 'stock.levels.report',
                'view_type': 'form',
                'view_mode': 'graph,tree',
                'context': ctx,
            }
        else:
            raise exceptions.except_orm(_("Error"), _("Your company does not have a warehouse"))


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    state = fields.Selection(track_visibility=False)

    @api.model
    def create(self, vals):
        # The creation messages are useless
        return super(StockPicking, self.with_context(mail_notrack=True, mail_create_nolog=True)).create(vals)


class StockSchedulerController(models.Model):
    _name = 'stock.scheduler.controller'
    _order = 'orderpoint_id'

    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint', string=u"Orderpoint", index=True)
    product_id = fields.Many2one('product.product', string=u"Product", readonly=True)
    location_id = fields.Many2one('stock.location', string=u"Location", readonly=True)
    location_sequence = fields.Integer(string=u"Location sequence", readonly=True)
    route_id = fields.Many2one('stock.location.route', string=u"Route", readonly=True)
    run_procs = fields.Boolean(string=u"Run procurements", readonly=True)
    job_creation_date = fields.Datetime(string=u"Job Creation Date", readonly=True)
    job_uuid = fields.Char(string=u"Job UUID", readonly=True, index=True)
    date_done = fields.Datetime(string=u"Date done")
    done = fields.Boolean(string=u"Done", index=True)
    company_id = fields.Many2one('res.company', string=u"Company", required=True, index=True)

    @api.multi
    def set_to_done(self):
        self.write({'done': True, 'date_done': fields.Datetime.now()})

    @api.multi
    def pop_job_orderpoint_process(self):
        for controller_line in self:
            job_uuid = process_orderpoints. \
                delay(ConnectorSession.from_env(self.env), 'stock.warehouse.orderpoint',
                      controller_line.orderpoint_id.ids, description="Computing orderpoints")
            controller_line.write({'job_uuid': job_uuid, 'job_creation_date': fields.Datetime.now()})

    @api.model
    def get_stock_scheduler_blocking_job_function_names(self):
        return ['openerp.addons.stock_procurement_just_in_time.stock_procurement_jit.pop_sub_process_orderpoints',
                'openerp.addons.scheduler_async.scheduler_async.run_procure_orderpoint_async']

    @api.model
    def is_any_stock_scheduler_blocking_process(self):
        return self.env['queue.job']. \
            search([('job_function_id.name', 'in', self.get_stock_scheduler_blocking_job_function_names()),
                    ('state', 'not in', ('done', 'failed'))], limit=1)

    @api.model
    def is_head_scheduler_function_running(self):
        return self.env['queue.job']. \
            search(
            [('job_function_id.name', '=',
              'openerp.addons.scheduler_async.scheduler_async.run_procure_orderpoint_async'),
             ('state', 'not in', ('done', 'failed'))], limit=1)

    @api.model
    def update_scheduler_controller(self, jobify=True, run_procurements=True):
        line_min_sequence = self.search([('done', '=', False)], order='location_sequence', limit=1)
        if self.is_any_stock_scheduler_blocking_process():
            return
        if line_min_sequence:
            min_sequence = line_min_sequence.location_sequence
            is_procs_confirmation_ok = self.env['procurement.order'].is_procs_confirmation_ok()
            is_moves_confirmation_ok = self.env['procurement.order'].is_moves_confirmation_ok()
            if is_procs_confirmation_ok and is_moves_confirmation_ok:
                controller_lines_no_run = self.search([('done', '=', False),
                                                       ('job_uuid', '=', False),
                                                       ('location_sequence', '=', min_sequence),
                                                       ('run_procs', '=', False)])

                if not controller_lines_no_run:
                    controller_lines_no_run_blocked = self.search([('done', '=', False),
                                                                   ('job_uuid', '!=', False),
                                                                   ('location_sequence', '=', min_sequence),
                                                                   ('run_procs', '=', False)])
                    if controller_lines_no_run_blocked:
                        any_line_to_relaunch = False
                        for line_blocked in controller_lines_no_run_blocked:
                            queue_job = self.env['queue.job'].search(
                                [('uuid', '=', line_blocked.job_uuid), ('state', 'in', ['done', 'failed'])])
                            if queue_job:
                                line_blocked.done = True
                            elif not self.env['queue.job'].search([('uuid', '=', line_blocked.job_uuid)]):
                                line_blocked.job_uuid = False
                                any_line_to_relaunch = True
                        if any_line_to_relaunch:
                            return

                    controller_lines_run_procs = self.search([('done', '=', False),
                                                              ('location_sequence', '=', min_sequence),
                                                              ('run_procs', '=', True)])
                    if controller_lines_run_procs:
                        if run_procurements:
                            self.env['procurement.order'].with_context(jobify=jobify).run_confirm_procurements()
                        else:
                            _logger.info(u"No procurement confirmation required")
                        controller_lines_run_procs.set_to_done()
                else:
                    if jobify:
                        while controller_lines_no_run:
                            chunk_line = controller_lines_no_run[:POP_PROCESS_CHUNK]
                            controller_lines_no_run = controller_lines_no_run[POP_PROCESS_CHUNK:]
                            _logger.info(u"Launch jobs to pop orderpoints jobs for %s controler lines, %s remaining",
                                         len(chunk_line), len(controller_lines_no_run))
                            job_uuid = pop_sub_process_orderpoints. \
                                delay(ConnectorSession.from_env(self.env), 'stock.scheduler.controller',
                                      chunk_line.ids, description="Pop job Computing orderpoints")
                            chunk_line.write({'job_uuid': job_uuid,
                                              'job_creation_date': fields.Datetime.now()})
                            # We want the stock scheduler to start immediately
                            self.env.cr.commit()
                    else:
                        for line in controller_lines_no_run:
                            line.job_uuid = str(line.orderpoint_id.id)
                            self.env.context = dict(self.env.context, job_uuid=line.job_uuid)
                            process_orderpoints(ConnectorSession.from_env(self.env), 'stock.warehouse.orderpoint',
                                                line.orderpoint_id.ids)

    @api.model
    def clean_scheduler_controller_lines(self):
        limit_date = fields.Datetime.to_string(dt.now() - relativedelta(days=10))
        items_to_unlink = self.search([('done', '=', True), ('date_done', '<', limit_date)])
        items_to_unlink.unlink()
