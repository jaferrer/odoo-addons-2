# -*- coding: utf-8 -*-
from openerp import models, fields, api
from datetime import datetime, timedelta
from openerp.addons.connector.session import ConnectorSession, ConnectorSessionHandler
from openerp.addons.connector.queue.job import job


@job
def refresh_materialized_view_job(session, model_name, ids):

    model_instance = session.pool[model_name]

    handler = ConnectorSessionHandler(session.cr.dbname, session.uid, session.context)
    with handler.session() as session:
        result = model_instance.refresh_materialized_view(session.cr, session.uid, ids, context=session.context)

    return result

MATERIALIZED_SQL_VIEW_STATES = [('nonexistent', 'Nonexistent'),
                                ('creating', 'Creating'),
                                ('refreshing', 'Refreshing'),
                                ('refreshed', 'Refreshed'),
                                ('aborted', 'Aborted'),
                                ]


class MaterializedSqlView(models.Model):
    _name = 'materialized.sql.view'
    _description = u"Materialized SQL View"

    name = fields.Char(u'Name', required=True)
    model_id = fields.Many2one('ir.model', u'Model', required=True, delete='cascade', readonly=True)
    view_name = fields.Char(u'SQL view name', required=True, readonly=True)
    matview_name = fields.Char(u'Materialized SQL View Name', required=True, readonly=True)
    pg_version = fields.Integer(u'Mat view pg version', required=True, readonly=True)
    sql_definition = fields.Text(u'sql', required=True, readonly=True)
    last_refresh_start_date = fields.Datetime(u'Last refreshed start date', readonly=True)
    last_refresh_end_date = fields.Datetime(u'Last refreshed end date', readonly=True)
    last_error_message = fields.Text(u'Last error', readonly=True)
    state = fields.Selection(MATERIALIZED_SQL_VIEW_STATES, u'State',
                             required=True, readonly=True, default='nonexistent')
    cron_id = fields.Integer(string='ref_cron_id')

    @api.multi
    def launch_refresh_materialized_sql_view(self):
        if self.env.context.get('ascyn', True):
            self.schedul_refresh_materialized_sql_view()
            return self.write({
                'state': 'refreshing'
            })
        else:
            return self.refresh_materialized_view()

    @api.multi
    def schedul_refresh_materialized_sql_view(self):
        uid = self.env.context.get('delegate_user', self.env.uid)
        vals = {
            'name': u"Refresh materialized views",
            'user_id': uid,
            'priority': 100,
            'numbercall': 1,
            'doall': True,
            'model': self._name,
            'function': 'refresh_materialized_view',
            'args': repr((self.ids, self.env.context)),
        }
        # use super user id because ir.cron have not to be accessible to normal user
        self.env['ir.cron'].sudo().create(vals)

    @api.model
    def refresh_materialized_view_by_name(self, mat_view_name=''):
        ids = self.search_materialized_sql_view_ids_from_matview_name(mat_view_name)
        return ids.refresh_materialized_view()

    @api.multi
    def refresh_materialized_view(self):
        result = []
        matviews_performed = []
        ir_model = self.env['ir.model']
        for matview in self.read(['id', 'model_id', 'matview_name'],
                                 load='_classic_write'):
            if matview['matview_name'] in matviews_performed:
                continue
            model = ir_model.browse(int(matview['model_id'])).read(['model'])
            matview_mdl = self.env[model[0]['model']]
            result.append(matview_mdl.refresh_materialized_view())
            matviews_performed.append(matview['matview_name'])
        return result

    @api.model
    def create_if_not_exist(self, values):
        if self.search([('model_id.model', '=', values['model_name']),
                        ('view_name', '=', values['view_name']),
                        ('matview_name', '=', values['matview_name']),
                        ], count=True) == 0:
            ir_mdl = self.env['ir.model']
            model_id = ir_mdl.search([('model', '=', values['model_name'])])
            values.update({'model_id': model_id[0].id})
            if not values.get('name'):
                name = model_id.read(['name'])[0]['name']
                values.update({'name': name})
            values.pop('model_name')
            self.create(values)

            result = self.search([('model_id', '=', values['model_id']),
                                  ('view_name', '=', values['view_name']),
                                  ('matview_name', '=', values['matview_name']),
                                  ])

            for item in result:
                if item.cron_id == 0:
                    item.create_schedul_refresh_materialized_sql_view()

    @api.model
    def _refresh_model(self, ids):
        uid = self.env.context.get('delegate_user', self.env.user.id)
        session = ConnectorSession(self._cr, uid, self._context)
        refresh_materialized_view_job.delay(session, 'materialized.sql.view', ids, description="")

    @api.multi
    def create_schedul_refresh_materialized_sql_view(self):
        uid = self.env.context.get('delegate_user', self.env.user.id)
        now = fields.Date.to_string(datetime.now() + timedelta(days=1)) + " 00:00:00"
        vals = {
            'name': u"Refresh materialized views %s" % (self.matview_name),
            'user_id': uid,
            'priority': 100,
            'interval_type': 'days',
            'numbercall': -1,
            'nextcall': now,
            'doall': False,
            'model': self._name,
            'function': '_refresh_model',
            'args': repr([self.ids]),
            'active': True
        }
        result = self.env['ir.cron'].sudo().create(vals)
        self.cron_id = result.id

    @api.multi
    def _get_cron(self):
        result = self.env['ir.cron'].search([('id', '=', self.cron_id)])
        return result

    @api.multi
    def open_cron_window(self):
        cron = self._get_cron()
        if cron:
            return {
                'name': 'cron',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'ir.cron',
                'res_id': self.cron_id,
                'type': 'ir.actions.act_window'
            }
        else:
            self.write({"cron_id": 0})

    @api.multi
    def schedul_refresh_materialized_sql_view(self):
        self.ensure_one()
        self._refresh_model(self.ids)

    @api.multi
    def delete_schedul_refresh_materialized_sql_view(self):
        self.ensure_one()
        cron = self._get_cron()
        if cron:
            cron.sudo().unlink()
        self.write({"cron_id": 0})

    def search_materialized_sql_view_ids_from_matview_name(self,  matview_name):
        return self.search([('matview_name', '=', matview_name)])

    @api.model
    def before_create_view(self, matview_name):
        values = {
            'last_refresh_start_date': datetime.now(),
            'state': 'creating',
            'last_error_message': ''
        }
        return self.write_values(matview_name, values)

    @api.model
    def before_refresh_view(self, matview_name):
        values = {
            'last_refresh_start_date': datetime.now(),
            'state': 'refreshing',
            'last_error_message': ''
        }
        return self.write_values(matview_name, values)

    @api.model
    def after_refresh_view(self, matview_name):
        values = {'last_refresh_end_date': datetime.now(),
                  'state': 'refreshed',
                  'last_error_message': '',
                  }
        pg_version = self.env.cr._cnx.server_version
        if self.env.context.get('values'):
            vals = self.env.context.get('values')
            pg_version = vals.get('pg_version', pg_version)
            if vals.get('sql_definition'):
                values.update({'sql_definition': vals.get('sql_definition')})
            if vals.get('view_name'):
                values.update({'view_name': vals.get('view_name')})
        values.update({'pg_version': pg_version})
        return self.write_values(matview_name, values)

    @api.model
    def after_drop_view(self, matview_name):
        return self.write_values(matview_name,
                                 {
                                     'state': 'nonexistent',
                                     'last_error_message': ''
                                 })

    @api.model
    def write_values(self, matview_name, values):
        ids = self.search_materialized_sql_view_ids_from_matview_name(matview_name)
        return ids.write(values)

    @api.model
    def aborted_matview(self, matview_name):
        return self.write_values(matview_name,
                                 {'state': 'aborted',
                                  'last_refresh_end_date': datetime.now(),
                                  'last_error_message': self.env.context.get('error_message',
                                                                             'Error not difined')
                                  })
