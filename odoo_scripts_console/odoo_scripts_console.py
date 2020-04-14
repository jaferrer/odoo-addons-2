from opcode import opmap

from odoo.tools.safe_eval import safe_eval, _SAFE_OPCODES as NEW_SAFE_OPCODES

import odoo
from odoo import models, fields, api, exceptions

# Monkey patch to be able to print inside odoo console
NEW_SAFE_OPCODES = NEW_SAFE_OPCODES.union(set(opmap[x] for x in ['PRINT_ITEM', 'PRINT_NEWLINE'] if x in opmap))

odoo.tools.safe_eval._SAFE_OPCODES = NEW_SAFE_OPCODES

FORBIDDEN_SQL_KEYWORDS = ["UPDATE", "INSERT", "ALTER", "DELETE", "GRANT", "DROP"]


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
        self.last_execution_begin = fields.Datetime.now()
        safe_eval(self.script, globals(), locals(), "exec")
        self.last_execution_end = fields.Datetime.now()
        if autocommit:
            self.env.cr.commit()


class OdooScriptWatcher(models.Model):
    _name = 'odoo.script.watcher'
    _inherit = ['mail.thread']
    _track = {
        'has_result': {
            'odoo_scripts_console.mt_watcher_result':
                lambda self, cr, uid, obj, ctx=None: obj.has_result or not obj.has_result
        },
        'nb_lines': {
            'odoo_scripts_console.mt_watcher_result':
                lambda self, cr, uid, obj, ctx=None: obj.nb_lines > 0 or not obj.nb_lines == 0
        },
    }

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
            watcher.with_delay(description=u"Updating watcher %s" % watcher.id).watch()
