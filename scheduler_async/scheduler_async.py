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

from openerp import fields, models, api
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import job


MOVE_CHUNK = 100


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


@job
def run_or_check_procurements(session, model_name, domain, action, context):
    """Tries to confirms all procurements that can be found with domain"""
    proc_obj = session.env[model_name].with_context(context)
    prev_procs = proc_obj
    while True:
        procs = proc_obj.sudo().search(domain)
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

    @api.model
    def run_assign_moves(self):
        confirmed_moves = self.env['stock.move'].search([('state', '=', 'confirmed')], limit=None,
                                                        order='priority desc, date_expected asc')

        while confirmed_moves:
            if self.env.context.get('jobify'):
                assign_moves.delay(ConnectorSession.from_env(self.env), 'stock.move', confirmed_moves[:100].ids,
                                   self.env.context)
            else:
                assign_moves(ConnectorSession.from_env(self.env), 'stock.move', confirmed_moves[:100].ids,
                             self.env.context)
            confirmed_moves = confirmed_moves[100:]

    @api.model
    def run_scheduler_async(self, use_new_cursor=False, company_id=False):
        proc_compute = self.env['procurement.order.compute.all'].create({})
        proc_compute.procure_calculation()

    @api.model
    def run_scheduler(self, use_new_cursor=False, company_id=False):
        """New scheduler function to run async jobs.

        This function overwrites the function with the same name from modules stock and procurement."""
        dom = []
        if company_id:
            dom += [('company_id', '=', company_id)]

        # Run confirmed procurements
        run_dom = dom + [('state', '=', 'confirmed')]
        if self.env.context.get("jobify", False):
            run_or_check_procurements.delay(ConnectorSession.from_env(self.env), 'procurement.order', run_dom, 'run',
                                            self.env.context)
        else:
            run_or_check_procurements(ConnectorSession.from_env(self.env), 'procurement.order', run_dom, 'run',
                                      self.env.context)

        # Run minimum stock rules
        without_job = not self.env.context.get("jobify", False)
        self.with_context(without_job=without_job).sudo()._procure_orderpoint_confirm(use_new_cursor=True,
                                                                                      company_id=company_id)

        # Check if running procurements are done
        check_dom = dom + [('state', '=', 'running')]
        if self.env.context.get("jobify", False):
            run_or_check_procurements.delay(ConnectorSession.from_env(self.env), 'procurement.order', check_dom,
                                            'check', self.env.context)
        else:
            run_or_check_procurements(ConnectorSession.from_env(self.env), 'procurement.order', check_dom,
                                      'check', self.env.context)

        # Try to assign moves
        self.run_assign_moves()
