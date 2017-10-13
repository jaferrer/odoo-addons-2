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

from openerp import api, models, fields
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.exception import RetryableJobError

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
def run_or_check_procurements(session, model_name, domain, action, context):
    """Confirm or check procurements"""
    job_uuid = session.context.get('job_uuid')
    proc_obj = session.env[model_name].with_context(context)
    prev_procs = proc_obj
    not_runned_yet = True
    while True:
        procs = proc_obj.sudo().search(domain)
        if procs:
            session.env.cr.execute("""SELECT
            po.id
            FROM procurement_order po
            WHERE po.id IN %s AND (
                po.run_or_confirm_job_uuid IS NULL or po.run_or_confirm_job_uuid = %s
            )""", (tuple(procs.ids), job_uuid))
            res = session.env.cr.fetchall()
            proc_ids = [item[0] for item in res]
            if not_runned_yet and procs and not proc_ids:
                # In case the job runs before the procs have been assigned their job uuid
                raise RetryableJobError("No procurements found for this job's UUID")
            procs = proc_obj.sudo().search([('id', 'in', proc_ids)])
        if not procs or prev_procs == procs:
            break
        else:
            prev_procs = procs
        if action == 'run':
            procs.sudo().run(autocommit=True)
        elif action == 'check':
            procs.sudo().check(autocommit=True)
        session.commit()


@job
def confirm_moves(session, model_name, ids, context):
    """Confirm draft moves"""
    job_uuid = session.context.get('job_uuid')
    move_obj = session.env[model_name].with_context(context)
    not_runned_yet = True
    if ids:
        session.env.cr.execute("""SELECT
            sm.id
            FROM stock_move sm
            WHERE sm.id IN %s AND (
                sm.confirm_job_uuid IS NULL or sm.confirm_job_uuid = %s
            )""", (tuple(ids), job_uuid))
        res = session.env.cr.fetchall()
        move_ids = [item[0] for item in res]
        if not_runned_yet and not move_ids:
            # In case the job runs before the moves have been assigned their job uuid
            raise RetryableJobError("No moves found for this job's UUID")
        moves = move_obj.search([('id', 'in', move_ids)])
        moves.action_confirm()


@job(default_channel='root.asgnmoves')
def assign_moves(session, model_name, ids, context):
    """Assign confirmed moves"""
    moves = session.env[model_name].with_context(context).browse(ids)
    moves.action_assign()


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
    def run_confirm_moves(self):
        group_draft_moves = {}

        all_draft_moves = self.env['stock.move'].search([('state', '=', 'draft')], limit=None,
                                                        order='priority desc, date_expected asc')

        all_draft_moves_ids = all_draft_moves.read(['id', 'group_id', 'location_id', 'location_dest_id'], load=False)

        for move in all_draft_moves_ids:
            key = (move['group_id'], move['location_id'], move['location_dest_id'])
            if key not in group_draft_moves:
                group_draft_moves[key] = []
            group_draft_moves[key].append(move['id'])

        for draft_move_ids in group_draft_moves:
            if self.env.context.get('jobify'):
                job_uuid = confirm_moves.delay(ConnectorSession.from_env(self.env), 'stock.move',
                                               group_draft_moves[draft_move_ids],
                                               dict(self.env.context))
                # We want to write confirm_job_uuid only if the move has none
                # or if the uuid points to a done or cancelled job
                self.env.cr.execute("""SELECT sm.confirm_job_uuid
FROM stock_move sm
  INNER JOIN queue_job qj ON qj.uuid = sm.confirm_job_uuid
WHERE sm.confirm_job_uuid IS NOT NULL AND qj.state IN ('done', 'failed')
GROUP BY sm.confirm_job_uuid""")
                done_or_failed_uuids = [item[0] for item in self.env.cr.fetchall()]
                moves_for_job = self.env['stock.move'].search([('id', 'in', group_draft_moves[draft_move_ids]),
                                                               '|', ('confirm_job_uuid', '=', False),
                                                               ('confirm_job_uuid', 'in', done_or_failed_uuids)])
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
        base_dom = [('state', '=', 'confirmed')]
        if company_id:
            base_dom += [('company_id', '=', company_id)]
        products = self.env['product.product'].search([], limit=PRODUCT_CHUNK)
        offset = 0
        while products:
            dom = base_dom + [('product_id', 'in', products.ids)]
            if self.env.context.get('jobify', False):
                job_uuid = run_or_check_procurements.delay(ConnectorSession.from_env(self.env),
                                                           'procurement.order', dom,
                                                           'run', dict(self.env.context))
                # We want to write run_or_confirm_job_uuid only if the proc has none
                # or if the uuid points to a done or cancelled job
                self.env.cr.execute("""SELECT po.run_or_confirm_job_uuid
FROM procurement_order po
  INNER JOIN queue_job qj ON qj.uuid = po.run_or_confirm_job_uuid
WHERE po.run_or_confirm_job_uuid IS NOT NULL AND qj.state IN ('done', 'failed')
GROUP BY po.run_or_confirm_job_uuid""")
                done_or_failed_uuids = [item[0] for item in self.env.cr.fetchall()]
                procs_for_job = self.search(dom + ['|', ('run_or_confirm_job_uuid', '=', False),
                                                   ('run_or_confirm_job_uuid', 'in', done_or_failed_uuids)])
                procs_for_job.write({'run_or_confirm_job_uuid': job_uuid})
            else:
                run_or_check_procurements(ConnectorSession.from_env(self.env), 'procurement.order', dom,
                                          'run', dict(self.env.context))
            offset += PRODUCT_CHUNK
            products = self.env['product.product'].search([], limit=PRODUCT_CHUNK, offset=offset)

    @api.model
    def run_check_procurements(self, company_id=None):
        """Launches the job to check all procurements."""
        base_dom = [('state', '=', 'running')]
        if company_id:
            base_dom += [('company_id', '=', company_id)]
        products = self.env['product.product'].search([], limit=PRODUCT_CHUNK)
        offset = 0
        while products:
            dom = base_dom + [('product_id', 'in', products.ids)]
            if self.env.context.get('jobify', False):
                job_uuid = run_or_check_procurements.delay(ConnectorSession.from_env(self.env), 'procurement.order',
                                                           dom, 'check', dict(self.env.context))
                # We want to write run_or_confirm_job_uuid only if the proc has none
                # or if the uuid points to a done or cancelled job
                self.env.cr.execute("""SELECT po.run_or_confirm_job_uuid
FROM procurement_order po
  INNER JOIN queue_job qj ON qj.uuid = po.run_or_confirm_job_uuid
WHERE po.run_or_confirm_job_uuid IS NOT NULL AND qj.state IN ('done', 'failed')
GROUP BY po.run_or_confirm_job_uuid""")
                done_or_failed_uuids = [item[0] for item in self.env.cr.fetchall()]
                procs_for_job = self.search(dom + ['|', ('run_or_confirm_job_uuid', '=', False),
                                                   ('run_or_confirm_job_uuid', 'in', done_or_failed_uuids)])
                procs_for_job.write({'run_or_confirm_job_uuid': job_uuid})
            else:
                run_or_check_procurements(ConnectorSession.from_env(self.env), 'procurement.order', dom,
                                          'check', dict(self.env.context))
            offset += PRODUCT_CHUNK
            products = self.env['product.product'].search([], limit=PRODUCT_CHUNK, offset=offset)

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
        without_job = not self.env.context.get("jobify", False)
        self.with_context(without_job=without_job).sudo()._procure_orderpoint_confirm(use_new_cursor=True,
                                                                                      company_id=company_id)

        # Check if running procurements are done
        self.run_check_procurements(company_id)

        # Try to assign moves
        self.run_assign_moves()


class StockMoveAsync(models.Model):
    _inherit = 'stock.move'

    confirm_job_uuid = fields.Char(tring=u"Job UUID to confirm this move")
