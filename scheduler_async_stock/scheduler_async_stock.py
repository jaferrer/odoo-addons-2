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
def run_procure_orderpoint_async(session, model_name, ids):
    """Compute minimum stock rules only"""
    compute_orederpoint_wizard = session.pool[model_name]
    res = compute_orederpoint_wizard._procure_calculation_orderpoint(session.cr, session.uid, ids,
                                                                     context=session.context)
    log = res.get('log',"")
    log += "Scheduler ended compute_all job."
    return log


class procurement_compute_async(models.TransientModel):
    _inherit = 'procurement.orderpoint.compute'

    @api.multi
    def _procure_calculation_orderpoint(self):
        proc_obj = self.env['procurement.order']
        company_id = self.env.user.company_id.id
        proc_obj._procure_orderpoint_confirm(use_new_cursor=self.env.cr.dbname, company_id=company_id)
        return {}

    @api.multi
    def procure_calculation(self):
        session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
        run_procure_orderpoint_async.delay(session, 'procurement.orderpoint.compute', self.ids)
        return {'type': 'ir.actions.act_window_close'}
