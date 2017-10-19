# -*- coding: utf8 -*-
#
# Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api, fields
from openerp.tools import config


class QueueJob(models.Model):
    _inherit = 'queue.job'

    @api.multi
    def set_to_done(self):
        """Sets to done the given jobs if they are not running."""
        for job in self:
            job.button_done()

    @api.model
    def enqueue_oudated_jobs(self):
        started_jobs = self.search([('state', '=', 'started')])
        worker_real_limit_seconds = config.parser.get_option_group('limit_time_real') or 120
        jobs_to_enqueue = self
        for job in started_jobs:
            ref_date = job.eta or job.date_started
            time_delta_seconds = (dt.now() - fields.Datetime.from_string(ref_date)).seconds
            if time_delta_seconds > worker_real_limit_seconds:
                jobs_to_enqueue |= job
        jobs_to_enqueue.requeue()

    @api.multi
    def _subscribe_users(self):
        """ Subscribe all users having the 'Connector Manager' group """
        group = self.env.ref('connector_improved.group_connector_real_manager')
        if not group:
            return
        companies = self.mapped('company_id')
        domain = [('groups_id', '=', group.id)]
        if companies:
            domain.append(('company_id', 'child_of', companies.ids))
        users = self.env['res.users'].search(domain)
        self.message_subscribe_users(user_ids=users.ids)

    @api.model
    def create(self, vals):
        # The creation message is useless
        return super(QueueJob, self.with_context(mail_notrack=True, mail_create_nolog=True)).create(vals)

    @api.multi
    def write(self, vals):
        # The fail message is useless
        return super(QueueJob, self.with_context(mail_notrack=vals.get('state') == 'failed')).write(vals)


class ConnectorCheckpointImproved(models.Model):
    _inherit = 'connector.checkpoint'

    @api.multi
    def _subscribe_users(self):
        """ Subscribe all users having the 'Connector Manager' group """
        group = self.env.ref('connector_improved.group_connector_real_manager')
        if not group:
            return
        users = self.env['res.users'].search([('groups_id', '=', group.id)])
        self.message_subscribe_users(user_ids=users.ids)
