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

import psycopg2
from openerp.addons.connector.exception import RetryableJobError
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession

from openerp import api, models, fields

PROC_CHUNK = 100
MOVE_CHUNK = 100
PRODUCT_CHUNK = 100


@job
def run_procure_all_async(session, model_name, company_id, context):
    """Launch all schedulers"""
    compute_all_wizard = session.env[model_name].with_context(context)
    compute_all_wizard._procure_calculation_all(company_id)
    return "Scheduler ended compute_all job."


@job
def run_procure_orderpoint_async(session, model_name, company_id, context):
    """Compute minimum stock rules only"""
    compute_orderpoint_wizard = session.env[model_name].with_context(context)
    compute_orderpoint_wizard._procure_calculation_orderpoint(company_id)
    return "Scheduler ended compute_orderpoint job."


@job(default_channel='root.confprocs')
def run_or_check_procurements(session, model_name, proc_for_job_ids, action, context):
    """Confirm or check procurements"""
    if not proc_for_job_ids:
        return
    try:
        session.env.cr.execute("""SELECT id FROM procurement_order WHERE id IN %s FOR UPDATE NOWAIT""",
                               (tuple(proc_for_job_ids),))
    except psycopg2.OperationalError:
        session.env.cr.rollback()
        return "Conflict detected with another job"
    job_uuid = session.context.get('job_uuid')
    job = job_uuid and session.env['queue.job'].search([('uuid', '=', job_uuid)]) or session.env['queue.job']
    proc_obj = session.env[model_name].with_context(context)
    prev_procs = proc_obj
    while True:
        procs = proc_obj.sudo().search([('id', 'in', proc_for_job_ids)])
        if procs:
            session.env.cr.execute("""SELECT po.id
FROM procurement_order po
WHERE po.id IN %s AND (po.run_or_confirm_job_uuid IS NULL OR po.run_or_confirm_job_uuid = %s)""",
                                   (tuple(procs.ids), job_uuid))
            res = session.env.cr.fetchall()
            proc_ids = [item[0] for item in res]
            if procs and not proc_ids:
                # In case the job runs before the procs have been assigned their job uuid
                msg = "No procurements found for this job's UUID"
                if job and job.max_retries and job.retry >= job.max_retries:
                    return msg
                raise RetryableJobError(msg)
            procs = proc_obj.sudo().search([('id', 'in', proc_ids)])
        if not procs or prev_procs == procs:
            break
        else:
            prev_procs = procs
        if action == 'run':
            procs.sudo().with_context(job_uuid=job_uuid).run()
        elif action == 'check':
            procs.sudo().with_context(job_uuid=job_uuid).check()
        moves_to_run = session.env['stock.move'].search([('procurement_id', 'in', procs.ids),
                                                         ('state', '=', 'draft')])
        if moves_to_run:
            session.env['procurement.order'].run_confirm_moves(domain=[('id', 'in', moves_to_run.ids)])


@job
def confirm_moves(session, model_name, ids, context):
    """Confirm draft moves"""
    if not ids:
        return
    try:
        session.env.cr.execute("""SELECT id FROM stock_move WHERE id IN %s FOR UPDATE NOWAIT""", (tuple(ids),))
    except psycopg2.OperationalError:
        session.env.cr.rollback()
        return "Conflict detected with another confirmation job"
    job_uuid = session.context.get('job_uuid')
    job = job_uuid and session.env['queue.job'].search([('uuid', '=', job_uuid)]) or session.env['queue.job']
    move_obj = session.env[model_name].with_context(context)
    not_runned_yet = True
    session.env.cr.execute("""SELECT
        sm.id
        FROM stock_move sm
        WHERE sm.id IN %s AND (
            sm.confirm_job_uuid IS NULL OR sm.confirm_job_uuid = %s
        )""", (tuple(ids), job_uuid))
    res = session.env.cr.fetchall()
    move_ids = [item[0] for item in res]
    if not_runned_yet and not move_ids:
        # In case the job runs before the moves have been assigned their job uuid
        msg = "No moves found for this job's UUID"
        if job and job.max_retries and job.retry >= job.max_retries:
            return msg
        raise RetryableJobError(msg)
    moves = move_obj.search([('id', 'in', move_ids)])
    moves.action_confirm()
    return "Moves confirmed correctly"


@job(default_channel='root.asgnmoves')
def assign_moves(session, model_name, ids, context):
    """Assign confirmed moves"""
    moves = session.env[model_name].with_context(context).browse(ids)
    moves.action_assign()


@job(default_channel='root.root_actions_on_procs')
def job_cancel_procurement(session, model_name, ids):
    """Cancel procurements"""
    procs = session.env[model_name].search([('id', 'in', ids),
                                            ('state', '!=', 'cancel')])
    procs.cancel()


@job(default_channel='root.root_actions_on_procs')
def job_reconfirm_procurement(session, model_name, ids, vals):
    """Reconfirm procurements with new vals (if provided)"""
    procs = session.env[model_name].browse(ids)
    procs.cancel()
    procs.reset_to_confirmed()
    if vals:
        procs.write(vals)
    procs.run()


@job
def job_unlink_orderpoints(session, model_name, ids, context):
    """Unlink orderpoints"""
    orderpoints = session.env[model_name].with_context(context).browse(ids)
    orderpoints.unlink()


class ProcurementComputeAllAsync(models.TransientModel):
    _inherit = 'procurement.order.compute.all'

    @api.multi
    def _procure_calculation_all(self, company_id):
        proc_obj = self.env['procurement.order']
        proc_obj.run_scheduler(use_new_cursor=True, company_id=company_id)
        return {}

    @api.multi
    def procure_calculation(self):
        for company in self.env.user.company_id + self.env.user.company_id.child_ids:
            # Hack to get tests working correctly
            context = dict(self.env.context)
            context['jobify'] = True
            run_procure_all_async.delay(ConnectorSession.from_env(self.env), 'procurement.order.compute.all',
                                        company.id, context)
        return {'type': 'ir.actions.act_window_close'}


class ProcurementOrderPointComputeAsync(models.TransientModel):
    _inherit = 'procurement.orderpoint.compute'

    @api.multi
    def _procure_calculation_orderpoint(self, company_id):
        proc_obj = self.env['procurement.order']
        proc_obj._procure_orderpoint_confirm(use_new_cursor=self.env.cr.dbname, company_id=company_id)
        return {}

    @api.multi
    def procure_calculation(self):
        for company in self.env.user.company_id + self.env.user.company_id.child_ids:
            # Hack to get tests working correctly
            context = dict(self.env.context)
            context['jobify'] = True
            run_procure_orderpoint_async.delay(ConnectorSession.from_env(self.env), 'procurement.orderpoint.compute',
                                               company.id, context)
        return {'type': 'ir.actions.act_window_close'}


class ProcurementOrderAsync(models.Model):
    _inherit = 'procurement.order'

    run_or_confirm_job_uuid = fields.Char(tring=u"Job UUID to confirm or check this procurement")
    
    @api.model
    def create(self, vals):
        return super(ProcurementOrderAsync, self).create(vals)

    @api.multi
    def run(self, autocommit=False):
        if self:
            self.env.cr.execute("""SELECT po.id FROM procurement_order po WHERE po.id IN %s FOR UPDATE NOWAIT""",
                                (tuple(self.ids),))
        return super(ProcurementOrderAsync, self).run(autocommit=autocommit)

    @api.model
    def run_confirm_moves(self, domain=False):
        group_draft_moves = {}
        if not domain:
            domain = []

        all_draft_moves = self.env['stock.move'].search(domain + [('state', '=', 'draft')], limit=None,
                                                        order='priority desc, date_expected asc')
        all_draft_moves_ids = all_draft_moves.read(['id', 'group_id', 'location_id', 'location_dest_id'], load=False)

        for move in all_draft_moves_ids:
            key = (move['group_id'], move['location_id'], move['location_dest_id'])
            if key not in group_draft_moves:
                group_draft_moves[key] = []
            group_draft_moves[key].append(move['id'])

        for draft_move_ids in group_draft_moves:
            if self.env.context.get('jobify'):
                query = """SELECT sm.id
FROM stock_move sm
  LEFT JOIN queue_job qj ON qj.uuid = sm.confirm_job_uuid
WHERE (qj.id IS NULL OR qj.state IN ('done', 'failed')) AND sm.id IN %s"""
                job_uuid = confirm_moves.delay(ConnectorSession.from_env(self.env), 'stock.move',
                                               group_draft_moves[draft_move_ids],
                                               dict(self.env.context))
                # We want to write confirm_job_uuid only if the move has none
                # or if the uuid points to a done or cancelled job
                self.env.cr.execute(query, (tuple(group_draft_moves[draft_move_ids]),))
                moves_for_job_ids = [item[0] for item in self.env.cr.fetchall()]
                moves_for_job = self.env['stock.move'].search([('id', 'in', moves_for_job_ids)])
                moves_for_job.write({'confirm_job_uuid': job_uuid})
            else:
                confirm_moves(ConnectorSession.from_env(self.env), 'stock.move', group_draft_moves[draft_move_ids],
                              dict(self.env.context))

    @api.model
    def run_assign_moves(self):
        confirmed_moves = self.env['stock.move'].search([('state', '=', 'confirmed')], limit=None,
                                                        order='priority desc, date_expected asc')

        while confirmed_moves:
            if self.env.context.get('jobify'):
                assign_moves.delay(ConnectorSession.from_env(self.env), 'stock.move', confirmed_moves[:100].ids,
                                   dict(self.env.context))
            else:
                assign_moves(ConnectorSession.from_env(self.env), 'stock.move', confirmed_moves[:100].ids,
                             dict(self.env.context))
            confirmed_moves = confirmed_moves[100:]

    @api.model
    def run_confirm_procurements(self, company_id=None):
        """Launches the job to confirm all procurements."""
        self._do_procurements_run_or_check('confirmed', 'run', company_id)

    @api.model
    def launch_run_or_check_jobs_for_ids(self, action_to_do, proc_ids):
        job_uuid = run_or_check_procurements.delay(ConnectorSession.from_env(self.env),
                                                   'procurement.order', proc_ids, action_to_do, dict(self.env.context))
        procs_for_job = self.search([('id', 'in', proc_ids)])
        procs_for_job.write({'run_or_confirm_job_uuid': job_uuid})

    @api.model
    def _do_procurements_run_or_check(self, state, action_to_do, company_id=None):
        """Launches the job to confirm all procurements."""
        products = self.env['product.product'].search([], limit=PRODUCT_CHUNK)
        offset = 0
        query = """SELECT po.id
FROM procurement_order po
  LEFT JOIN queue_job qj ON qj.uuid = po.run_or_confirm_job_uuid
  WHERE (qj.id IS NULL OR qj.state IN ('done', 'failed')) AND
                      po.state = %s AND
                      po.product_id IN %s"""
        if company_id:
            query += """ AND po.company_id = %s"""
        while products:
            # We want to write run_or_confirm_job_uuid only if the proc has none
            # or if the uuid points to a done or cancelled job
            params = company_id and (state, tuple(products.ids), company_id,) or (state, tuple(products.ids),)
            self.env.cr.execute(query, params)
            proc_for_job_ids = [item[0] for item in self.env.cr.fetchall()]
            if self.env.context.get('jobify', False):
                if action_to_do == 'run':
                    for proc_id in proc_for_job_ids:
                        self.launch_run_or_check_jobs_for_ids(action_to_do, [proc_id])
                else:
                    self.launch_run_or_check_jobs_for_ids(action_to_do, proc_for_job_ids)
            else:
                run_or_check_procurements(ConnectorSession.from_env(self.env), 'procurement.order', proc_for_job_ids,
                                          'run', dict(self.env.context))
            offset += PRODUCT_CHUNK
            products = self.env['product.product'].search([], limit=PRODUCT_CHUNK, offset=offset)

    @api.model
    def run_check_procurements(self, company_id=None):
        """Launches the job to check all procurements."""
        self._do_procurements_run_or_check('running', 'check', company_id)

    @api.model
    def run_scheduler_async(self, use_new_cursor=False, company_id=False):
        proc_compute = self.env['procurement.order.compute.all'].create({})
        proc_compute.procure_calculation()

    @api.model
    def run_compute_orderpoints(self, use_new_cursor=False, company_id=False):
        proc_compute = self.env['procurement.orderpoint.compute'].create({})
        proc_compute.procure_calculation()

    @api.model
    def run_scheduler(self, use_new_cursor=False, company_id=False):
        """New scheduler function to run async jobs.

        This function overwrites the function with the same name from modules stock and procurement."""

        # Run confirmed procurements
        self.run_confirm_procurements(company_id)

        # Run minimum stock rules
        self.sudo()._procure_orderpoint_confirm(use_new_cursor=True, company_id=company_id)

        # Check if running procurements are done
        self.run_check_procurements(company_id)

        # Try to assign moves
        self.run_assign_moves()

    @api.model
    def is_procs_confirmation_ok(self):
        return not self.env['queue.job']. \
            search([('job_function_id.name', '=',
                     'openerp.addons.scheduler_async.scheduler_async.run_or_check_procurements'),
                    ('state', 'not in', ('done', 'failed'))], limit=1)

    @api.model
    def is_moves_confirmation_ok(self):
        return not self.env['queue.job']. \
            search([('job_function_id.name', '=',
                     'openerp.addons.scheduler_async.scheduler_async.confirm_moves'),
                    ('state', 'not in', ('done', 'failed'))], limit=1)

    @api.multi
    def launch_job_cancel_procurement(self):
        for proc_id in self.ids:
            job_cancel_procurement.delay(ConnectorSession.from_env(self.env), 'procurement.order', [proc_id])

    @api.multi
    def launch_job_reconfirm_procurement(self, vals=None):
        for proc_id in self.ids:
            job_reconfirm_procurement.delay(ConnectorSession.from_env(self.env), 'procurement.order',
                                            [proc_id], vals or {})

    @api.model
    def restart_proc_in_exception(self, jobify=True):
        """
        quand on annule un OF, son proc passe en exception =>
        ce cron relance les procurement en exception, par jobs de 100 procs, chaque nuit
        """
        proc_in_exception = self.env['procurement.order'].search([('state', '=', 'exception')])

        buffer = 100
        while proc_in_exception:
            chunk_procs = [p.id for p in proc_in_exception[:buffer]]
            if jobify:
                run_or_check_procurements.delay(ConnectorSession.from_env(self.env), 'procurement.order',
                                                chunk_procs, 'run', dict(self.env.context))
            else:
                run_or_check_procurements(ConnectorSession.from_env(self.env), 'procurement.order',
                                          chunk_procs, 'run', dict(self.env.context))
            proc_in_exception = proc_in_exception[buffer:]


class StockMoveAsync(models.Model):
    _inherit = 'stock.move'

    confirm_job_uuid = fields.Char(tring=u"Job UUID to confirm this move")

    @api.multi
    def action_confirm(self):
        if self:
            self.env.cr.execute("""SELECT sm.id FROM stock_move sm WHERE sm.id IN %s FOR UPDATE NOWAIT""",
                                (tuple(self.ids),))
        return super(StockMoveAsync, self).action_confirm()


class OrderpointAsync(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    @api.multi
    def launch_job_unlink_orderpoints(self):
        context = dict(self.env.context)
        for rec in self:
            job_unlink_orderpoints.delay(ConnectorSession.from_env(self.env), 'stock.warehouse.orderpoint',
                                         rec.ids, context)
