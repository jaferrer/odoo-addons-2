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

import base64
import xlsxwriter
import csv
import StringIO

from io import BytesIO
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import job
from openerp import models, fields, api, exceptions, _

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
    is_automatic = fields.Boolean(string=u"Is automatic", default=True)

    @api.multi
    def watch_multi(self):
        for rec in self:
            rec.watch()

    @api.multi
    def watch(self):
        self.ensure_one()
        query_upper = self.query.upper()
        for forbidden_keyword in FORBIDDEN_SQL_KEYWORDS:
            if forbidden_keyword in query_upper:
                raise exceptions.except_orm(u"Error!", u"Forbidden keyword %s in watcher query" % forbidden_keyword)

        query_with_header = "COPY (%s) TO STDOUT WITH CSV HEADER" % self.query.rstrip(';')
        output = StringIO.StringIO()
        self.env.cr.copy_expert(query_with_header, output)
        output.seek(0)
        res = csv.reader(output)
        rows_with_header = [row for row in res]
        len_row_without_header = len(rows_with_header) - 1
        if len_row_without_header:
            if self.nb_lines != len_row_without_header or not self.has_result:
                self.sudo().write({'has_result': True, 'nb_lines': len_row_without_header})
        elif self.has_result:
            self.sudo().write({'has_result': False, 'nb_lines': 0})
        return rows_with_header

    @api.multi
    def export(self):
        self.ensure_one()
        rows_with_header = self.watch()

        if not self.has_result:
            raise exceptions.Warning(_(u"No results to export!"))

        file_name = 'export_resultat_watcher_%i_du_%s' % (self.id, fields.Datetime.now())
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        style_title, style_text = self.define_styles(workbook)
        column_number = 0

        worksheet = workbook.add_worksheet(u"Resultats")

        # Création de la première ligne d'entête
        for head in rows_with_header[0]:
            head = unicode(head.decode('utf-8'))
            column_number = self.fill_column(worksheet, column_number, style_title, head)

        rows_with_header.pop(0)

        # Remplissage des lignes
        line_no = 0
        for row in rows_with_header:
            line_no += 1
            column_number = 0
            for value in row:
                value = unicode(value.decode('utf-8'))
                if value == 't':
                    value = _(u"True")
                elif value == 'f':
                    value = _(u"False")
                column_number = self.fill_line(worksheet, line_no, column_number, style_text, value or "")

        # Élargissement des colonnes
        worksheet.set_column(0, column_number, 30, None)

        # On fige la première ligne
        worksheet.freeze_panes(1, 0)

        workbook.close()
        data = output.getvalue()
        attachment = self.create_attachment(base64.encodestring(data), file_name + '.xlsx')
        url = "/web/binary/saveas?model=ir.attachment&field=datas&id=%s&filename_field=name" % attachment.id
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "self"
        }

    @api.multi
    def create_attachment(self, binary, name):
        self.ensure_one()
        if not binary:
            return False
        return self.env['ir.attachment'].sudo().create({
            'type': 'binary',
            'res_model': self._name,
            'res_name': name,
            'datas_fname': name,
            'name': name,
            'datas': binary,
            'res_id': self.id,
        })

    @api.model
    def define_styles(self, workbook):
        style_title = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 12,
            'valign': 'vcenter',
            'align': 'center',
            'text_wrap': True,
            'border': True,
            'bold': True,
        })
        style_text = workbook.add_format({
            'font_name': 'Arial Narrow',
            'font_size': 12,
            'valign': 'vcenter',
            'align': 'left',
            'text_wrap': True,
            'border': True,
        })

        return style_title, style_text

    @api.multi
    def fill_column(self, worksheet, column_number, style, name):
        worksheet.write(0, column_number, name, style)
        return column_number + 1

    @api.multi
    def fill_line(self, worksheet, line_no, column_number, style, value):
        worksheet.write(line_no, column_number, value, style)
        return column_number + 1

    @api.model
    def launch_jobs_watch_lines(self):
        watchers = self.search([('is_automatic', '=', True)])
        for watcher in watchers:
            session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
            job_launch_watchers.delay(session, 'odoo.script.watcher', watcher.ids,
                                      description="Launch watch: %s" % watcher.name)
