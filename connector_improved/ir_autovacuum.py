# -*- coding: utf8 -*-
#
#    Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession


@job
def job_power_on(session, model_name, context=None):
    model = session.env[model_name].with_context(context)
    model.power_on()
    return u"Auto-vacuum done"


class ConnectorImprovedIrAutovacuum(models.TransientModel):
    _inherit = 'ir.autovacuum'

    @api.model
    def launch_job_power_on(self):
        job_power_on.delay(ConnectorSession.from_env(self.env), 'ir.autovacuum', context=self.env.context.copy(),
                  description=u"Auto-vacuum internal data")
