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

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession

from openerp import models, fields, api


@job
def job_create_measure_of_disk_usage(session, model_name, table_ids):
    session.env[model_name].browse(table_ids).create_measure_of_disk_usage()


class OdooMonitoringDiskUsageByTable(models.Model):
    _name = 'odoo.monitoring.disk.usage.by.table'
    _order = 'date desc, cardinality desc'

    date = fields.Datetime(string=u"Date", required=True)
    table_id = fields.Many2one('odoo.monitoring.database.table', string=u"Table", readonly=True, required=True)
    cardinality = fields.Integer(string=u"Cardinality", readonly=True, group_operator='max')
    disk_size_data = fields.Float(string=u"Size on disk (data)", help=u"Unit is Gigabyte",
                                  readonly=True, group_operator='max')
    disk_size_index = fields.Float(string=u"Size on disk (index)", help=u"Unit is Gigabyte",
                                   readonly=True, group_operator='max')
    disk_size_total = fields.Float(string=u"Size on disk (total)", help=u"Unit is Gigabyte",
                                   readonly=True, group_operator='max')


class OdooMonitoringDatabaseTable(models.Model):
    _inherit = 'odoo.monitoring.database.table'
    _order = 'current_disk_size_total desc, name asc'

    disk_usage_line_ids = fields.One2many('odoo.monitoring.disk.usage.by.table', 'table_id',
                                          string=u"Measures of disk usage")
    current_cardinality = fields.Integer(string=u"Cardinality", compute='_compute_current_disk_usage', store=True,
                                         group_operator='max')
    current_disk_size_data = fields.Float(string=u"Size on disk (data)", help=u"Unit is Gigabyte",
                                          compute='_compute_current_disk_usage', store=True, group_operator='max')
    current_disk_size_index = fields.Float(string=u"Size on disk (index)", help=u"Unit is Gigabyte",
                                           compute='_compute_current_disk_usage', store=True, group_operator='max')
    current_disk_size_total = fields.Float(string=u"Size on disk (total)", help=u"Unit is Gigabyte",
                                           compute='_compute_current_disk_usage', store=True, group_operator='max')

    @api.multi
    @api.depends('disk_usage_line_ids')
    def _compute_current_disk_usage(self):
        for rec in self:
            last_disk_usage_measure = self.env['odoo.monitoring.disk.usage.by.table']. \
                search([('id', 'in', rec.disk_usage_line_ids.ids)], order='date desc', limit=1)
            rec.current_cardinality = last_disk_usage_measure and last_disk_usage_measure.cardinality or 0
            rec.current_disk_size_data = last_disk_usage_measure and last_disk_usage_measure.disk_size_data or 0
            rec.current_disk_size_index = last_disk_usage_measure and last_disk_usage_measure.disk_size_index or 0
            rec.current_disk_size_total = last_disk_usage_measure and last_disk_usage_measure.disk_size_total or 0

    @api.multi
    def create_measure_of_disk_usage(self):
        date = fields.Datetime.now()
        for rec in self:
            # An approximate value is enough for this usage, and much facster than a count(*)
            self.env.cr.execute("""SELECT *
FROM (
       SELECT table_name,
              row_estimate,
              total_bytes,
              index_bytes
       FROM (
              SELECT c.oid
                   , nspname                               AS tale_schema
                   , relname                               AS TABLE_NAME
                   , c.reltuples                           AS row_estimate
                   , pg_total_relation_size(c.oid)         AS total_bytes
                   , pg_indexes_size(c.oid)                AS index_bytes
                   , pg_total_relation_size(reltoastrelid) AS toast_bytes
              FROM pg_class c
                     LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
              WHERE relkind = 'r'
            ) a
     ) a
WHERE table_name = %s""", (rec.name,))
            data = self.env.cr.dictfetchall()[0]
            # We convert Bytes to GigaBytes
            self.env['odoo.monitoring.disk.usage.by.table'].create({
                'date': date,
                'table_id': rec.id,
                'cardinality': data['row_estimate'],
                'disk_size_data': float(data['total_bytes'] - data['index_bytes']) / 1000000000,
                'disk_size_index': float(data['index_bytes']) / 1000000000,
                'disk_size_total': float(data['total_bytes']) / 1000000000,
            })

    @api.model
    def cron_measure_of_disk_usage(self):
        for rec in self.search([]):
            job_create_measure_of_disk_usage.delay(ConnectorSession.from_env(self.env), self._name, rec.ids,
                                                   description=u"Update disk usage for table %s" % rec.name)

    @api.multi
    def view_cardinality_evolution(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        ctx['search_default_table_id'] = self.id
        ctx['search_default_group_by_day'] = True
        ctx['search_default_card_sup_10k_lines'] = True
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'graph',
            'view_id': self.env.ref('database_monitoring_disk_usage.odoo_monitoring_disk_measure_graph_cardinality').id,
            'res_model': 'odoo.monitoring.disk.usage.by.table',
            'context': ctx,
        }

    @api.multi
    def view_disk_usage_evolution(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        ctx['search_default_table_id'] = self.id
        ctx['search_default_group_by_day'] = True
        ctx['search_default_disk_size_sup_10Mb'] = True
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'graph',
            'view_id': self.env.ref('database_monitoring_disk_usage.odoo_monitoring_disk_measure_graph_disk_size').id,
            'res_model': 'odoo.monitoring.disk.usage.by.table',
            'context': ctx,
        }
