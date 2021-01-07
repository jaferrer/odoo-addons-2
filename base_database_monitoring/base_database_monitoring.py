# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession

from openerp import models, fields, api


_logger = logging.getLogger(__name__)


@job
def job_update_tables_list(session, model_name):
    session.env[model_name].update_tables_list()


class OdooMonitoringDatabaseTable(models.Model):
    _name = 'odoo.monitoring.database.table'

    name = fields.Char(string=u"Name", readonly=True, required=True)
    model_id = fields.Many2one('ir.model', string=u"Model", readonly=True)

    @api.model
    def cron_update_tables_list(self):
        job_update_tables_list.delay(ConnectorSession.from_env(self.env), self._name,
                                     description=u"Update table list for database monitoring")

    @api.model
    def update_tables_list(self):
        existing_tablenames = [item.name for item in self.search([])]
        self.env.cr.execute("""SELECT tablename
FROM pg_catalog.pg_tables
WHERE schemaname != 'pg_catalog'
  AND schemaname != 'information_schema';""")
        tables_dict = self.env.cr.dictfetchall()
        for item in tables_dict:
            tablename = item['tablename']
            if tablename not in existing_tablenames:
                data = {'name': tablename}
                for model in self.env['ir.model'].search([]):
                    try:
                        if self.env[model.model]._table == tablename:
                            data['model_id'] = model.id
                            break
                    except KeyError:
                        continue
                print "create %s" % data
                self.create(data)
        self.remove_not_existing_tables([item['tablename'] for item in tables_dict])

    @api.model
    def remove_not_existing_tables(self, table_names):
        for table in self.search([]):
            if table.name not in table_names:
                _logger.info("deleting not anymore existing table %s from size monitoring", table.name)
                table.unlink()
