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


@job
def run_procure_all_async(session, model_name, ids):
    """Launch all schedulers"""
    compute_all_wizard = session.pool[model_name]
    compute_all_wizard._procure_calculation_all(session.cr, session.uid, ids, context=session.context)
    return "Scheduler ended compute_all job."


class procurement_compute_async(models.TransientModel):
    _inherit = 'procurement.order.compute.all'

    @api.multi
    def _procure_calculation_all(self):
        proc_obj = self.env['procurement.order']
        user = self.env.user
        comps = [x.id for x in user.company_ids]
        for comp in comps:
            proc_obj.run_scheduler(use_new_cursor=True, company_id=comp)
        return {}

    @api.multi
    def procure_calculation(self):
        session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
        job_uuid = run_procure_all_async.delay(session, 'procurement.order.compute.all', self.ids)
        return {'type': 'ir.actions.act_window_close'}


class procurement_order_async(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def run_scheduler_async(self, use_new_cursor=False, company_id = False):
        proc_compute = self.env['procurement.order.compute.all'].create({})
        proc_compute.procure_calculation()


