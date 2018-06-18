# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from openerp.addons.connector.session import ConnectorSessionHandler, ConnectorSession


@job
def job_action_backup(session, model_name, ids):
    model_instance = session.pool[model_name]
    model_instance.action_backup(session.cr, session.uid, ids, context=session.context)
    return u"Database saved"


class DbBackupAsynchronous(models.Model):
    _inherit = 'db.backup'

    @api.model
    def action_backup_all(self):
        for backup in self.search([]):
            session = ConnectorSession.from_env(self.env)
            description = u"Database Backup with ID=%s" % backup.id
            job_action_backup.delay(session, 'db.backup', backup.ids, description=description)
