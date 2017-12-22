# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import job


from openerp import models, fields, api, exceptions


FORBIDDEN_SQL_KEYWORDS = ["UPDATE", "INSERT", "ALTER", "DELETE", "GRANT", "DROP"]


@job
def job_launch_watchers(session, model_name, ids):
    session.env[model_name].browse(ids).watch()
    return "Watch launched"


class OdooScript(models.Model):
    _name = 'odoo.script'

    name = fields.Char(string=u"Name", required=True)
    description = fields.Char(string=u"Description")
    script = fields.Text(string=u"Script to execute", required=True)
    last_execution_begin = fields.Datetime(string=u"Last execution begin", readonly=True)
    last_execution_end = fields.Datetime(string=u"Last execution end", readonly=True)
    console_browse_command = fields.Char(string=u"Console browse command",
                                         compute='_compute_console_browse_command')
    console_execute_command = fields.Char(string=u"Console execute command",
                                          compute='_compute_console_browse_command')

    @api.multi
    def _compute_console_browse_command(self):
        for rec in self:
            rec.console_browse_command = rec.id and "script = self.env['odoo.script'].browse(%s)" % rec.id or False
            rec.console_execute_command = rec.id and "self.env['odoo.script'].browse(%s).execute()" % rec.id or False

    @api.multi
    def list(self):
        scripts = self.search([])
        msg = u""
        for rec in scripts:
            rec_msg = rec.name + (u" (ID: %s)" % rec.id) + (rec.description and u" -> " + rec.description or u"")
            if msg:
                msg += u"\n"
            msg += rec_msg
        return msg

    @api.multi
    def execute(self, autocommit=False):
        self.ensure_one()
        glob = globals()
        loc = locals()
        self.last_execution_begin = fields.Datetime.now()
        exec (self.script, glob, loc)
        self.last_execution_end = fields.Datetime.now()
        if autocommit:
            self.env.cr.commit()
            print u"End of process, result committed"
        else:
            print u"End of process, you can commit or rollback"


class OdooScriptWatcher(models.Model):
    _name = 'odoo.script.watcher'
    _inherit = 'mail.thread'

    name = fields.Char(string=u"Name", required=True)
    description = fields.Char(string=u"Description")
    query = fields.Text(string=u"Query to execute", required=True)
    has_result = fields.Boolean(string=u"Has result", track_visibility='onchange', readonly=True, copy=False)
    nb_lines = fields.Integer(string=u"Number of lines detected", track_visibility='onchange', readonly=True,
                              copy=False)
    script_id = fields.Many2one('odoo.script', string=u"Linked script", copy=False)

    @api.multi
    def watch(self):
        self.ensure_one()
        query_upper = self.query.upper()
        for forbidden_keyword in FORBIDDEN_SQL_KEYWORDS:
            if forbidden_keyword in query_upper:
                raise exceptions.except_orm(u"Error!", u"Forbidden keyword %s in watcher query" % forbidden_keyword)
        self.env.cr.execute("""%s""" % self.query)
        res = self.env.cr.fetchall()
        if res:
            if self.nb_lines != len(res) or not self.has_result:
                self.write({'has_result': True, 'nb_lines': len(res)})
        elif self.has_result:
            self.write({'has_result': False, 'nb_lines': 0})

    @api.model
    def launch_jobs_watch_lines(self):
        watchers = self.search([])
        for watcher in watchers:
            session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
            job_launch_watchers.delay(session, 'odoo.script.watcher', watcher.ids,
                                      description="Launch watch: %s" % watcher.name)
