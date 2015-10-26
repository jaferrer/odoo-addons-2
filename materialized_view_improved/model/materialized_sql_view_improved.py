'''
Created on 20 oct. 2015

@author: asalaun
'''

from openerp import models, fields, api
from datetime import datetime,timedelta
from openerp.addons.connector.session import ConnectorSession, ConnectorSessionHandler
from openerp.addons.connector.queue.job import job


@job
def refresh_materialized_view_job(session, model_name, ids):

    model_instance = session.pool[model_name]

    handler = ConnectorSessionHandler(session.cr.dbname, session.uid, session.context)
    with handler.session() as session:
        result=model_instance.refresh_materialized_view(session.cr, session.uid, ids, context=session.context)

    return result

class MaterializedViewImproved(models.Model):
    _inherit = "materialized.sql.view"
    
    cron_id = fields.Integer(string='ref_cron_id')
    
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
            self.write({"cron_id":0})
            
    @api.multi
    def schedul_refresh_materialized_sql_view(self):
        self.ensure_one()
        self._refresh_model(self.ids)

    @api.multi
    def delete_schedul_refresh_materialized_sql_view(self) :
        self.ensure_one()
        cron = self._get_cron()
        if cron:
            cron.sudo().unlink()
        self.write({"cron_id":0})

    @api.multi
    def create_schedul_refresh_materialized_sql_view(self) :
        uid = self.env.context.get('delegate_user', self.env.user.id)
        now = fields.Date.to_string(datetime.now() + timedelta(days=1)) + " 00:00:00"
        vals = {
                'name': u"Refresh materialized views %s" % (self.matview_name),
                'user_id': uid,
                'priority': 100,
                'interval_type':'days',
                'numbercall': -1,
                'nextcall':now,
                'doall': True,
                'model': self._name,
                'function': '_refresh_model',
                'args': repr((self.ids)),
                'active': True
            }
        result = self.env['ir.cron'].sudo().create(vals)
        self.cron_id = result.id
        #self.cron=result

    @api.cr_uid_ids
    def refresh_materialized_view(self, cr, uid, ids, context=None):
        result = super(MaterializedViewImproved, self).refresh_materialized_view(cr, uid, ids, context=context)
        return result
    
    @api.model
    def _refresh_model(self, ids):
        uid = self.env.context.get('delegate_user', self.env.user.id)
        session = ConnectorSession(self._cr, uid, self._context)
        refresh_materialized_view_job.delay(session, 'materialized.sql.view', ids, description="")
