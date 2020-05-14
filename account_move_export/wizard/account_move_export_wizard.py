# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from io import BytesIO

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

from odoo.addons.queue_job.job import job


class AccountMoveExportWizard(models.TransientModel):
    _name = 'account.move.export.wizard'

    # Defaults for FTP
    @api.model
    def _get_default_ftp_url(self):
        return self.env['ir.config_parameter'].sudo().get_param('account_move_export.export_ftp_url', False)

    @api.model
    def _get_default_ftp_port(self):
        return self.env['ir.config_parameter'].sudo().get_param('account_move_export.export_ftp_port', False)

    @api.model
    def _get_default_ftp_login(self):
        return self.env['ir.config_parameter'].sudo().get_param('account_move_export.export_ftp_login', False)

    @api.model
    def _get_default_ftp_password(self):
        return self.env['ir.config_parameter'].sudo().get_param('account_move_export.export_ftp_password', False)

    @api.model
    def _get_default_ftp_path(self):
        return self.env['ir.config_parameter'].sudo().get_param('account_move_export.export_ftp_path', False)

    destination = fields.Selection([
        ('ftp', u"On FTP"),
        ('screen', u"On screen"),
    ], u"Extraction type", required=True, default='screen')
    line_selection = fields.Selection([
        ('bounded', u"From date to date"),
        ('manual', u"Manual moves selection"),
        ('not_exported', u"Lines not previously exported"),
    ], u"Line selection", required=True)
    journal_ids = fields.Many2many('account.journal', string=u"Journals")
    date_from = fields.Date(u"Date from")
    date_to = fields.Date(u"Date to")
    move_ids = fields.Many2many('account.move', string=u"Account moves")
    group_by_account = fields.Boolean(u"Group by accounting account", default=True)

    ftp_url = fields.Char(u"FTP URL", default=_get_default_ftp_url)
    ftp_port = fields.Char(u"FTP port", default=_get_default_ftp_port)
    ftp_login = fields.Char(u"FTP login", default=_get_default_ftp_login)
    ftp_password = fields.Char(u"FTP password", default=_get_default_ftp_password)
    ftp_path = fields.Char(u"FTP path", default=_get_default_ftp_path)

    binary_export = fields.Binary("Export file")
    data_fname = fields.Char("File name")

    @api.multi
    def action_validate(self):
        """ Called when someone validates the export wizard, or indirectly by the cron

        Trigger the export
        """
        self.ensure_one()

        journals = self.journal_ids or self.env['account.journal'].search([])

        moves = self.env['account.move']
        if self.line_selection == 'bounded':
            moves = self._get_moves_by_dates_and_journals(self.date_from, self.date_to, journals)
        elif self.line_selection == 'manual':
            moves = self.move_ids
        elif self.line_selection == 'not_exported':
            moves = self._get_unexported_moves(journals)

        self.binary_export = base64.encodestring(self._create_export_from_moves(moves))

        self.data_fname = self._get_export_filename()

        self._mark_move_lines_as_exported(moves)

        if self.destination == 'ftp':
            self._send_to_ftp()
        else:
            return self._onscreen_export()

    @api.multi
    def get_ftp_instance(self, host, port, username, password):
        """ Create a FTPWizard instance and return it """
        return self.env['ftp.wizard'].create({
            'host': host,
            'port': port or 21,
            'username': username,
            'password': password,
        })

    @api.model
    def cron_export_lines(self):
        """ Called from account_move_export_cron

        Automatically export some lines accordingly to the parameters specified in account config settings
        """
        note = u"Export des lignes comptables du %s" % fields.Date.today()
        self.with_delay(description=note)._run_export_lines()

    @api.model
    @job(default_channel='root.account')
    def _run_export_lines(self):
        get_param = self.env['ir.config_parameter'].get_param
        vals = {
            'destination': 'ftp',
            'line_selection': get_param('account_move_export.export_line_selection'),
            'journal_ids': [(6, 0, safe_eval(get_param('account_move_export.export_journal_ids', '[]')))],
            'group_by_account': safe_eval(get_param('account_move_export.export_group_by_account', 'False')),
            'ftp_url': get_param('account_move_export.export_ftp_url'),
            'ftp_login': get_param('account_move_export.export_ftp_login'),
            'ftp_password': get_param('account_move_export.export_ftp_password'),
            'ftp_path': get_param('account_move_export.export_ftp_path'),
        }
        if vals['line_selection'] == 'bounded':
            vals.update(
                date_from=get_param('account_move_export.export_date_from'),
                date_to=get_param('account_move_export.export_date_to'),
            )
        self.create(vals).action_validate()

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            name = _(u"Accounting export")
            if rec.line_selection == 'bounded':
                name += _(u" from %s to %s") % (rec.date_from, rec.date_to)
            if rec.line_selection != 'manual':
                name += _(u" on %s") % ', '.join(j.display_name for j in self.journal_ids)
            res.append((rec.id, name))
        return res

    @api.multi
    def _mark_move_lines_as_exported(self, moves):
        """ Mark lines of a recordset of account.move as exported, in order not to export them again

        :param moves: recordset of account.move
        """
        moves.mapped('line_ids').write({'exported': True})

    @api.multi
    def _get_moves_by_dates_and_journals(self, date_from, date_to, journals):
        """ Get all moves in selected journals in a date frame

        :param date_from: date or string, first bound of the frame
        :param date_to: date or string, second bound of the frame
        :param journals: recordset of account.journal
        :return: recordset of account.move
        """
        moves = self.env['account.move'].search([
            ('journal_id', 'in', journals.ids),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ])
        return moves

    @api.multi
    def _get_unexported_moves(self, journals):
        """ Get all move in the selected journals whose lines have not already been exported

        :param journals: recordset of account.journal
        :return: recordset of account.move
        """
        lines = self.env['account.move.line'].search_read([
            ('move_id.journal_id', 'in', journals.ids),
            ('exported', '=', False),
        ], ['move_id'])

        return self.env['account.move'].browse({line['move_id'][0] for line in lines})

    @api.multi
    def _create_export_from_moves(self, moves):
        """ Creates the export from a recorset of account.move

        MUST BE IMPLEMENTED BY A SPECIFIC MODULE
        The current module only provides structure and interface for exports

        :param moves: recordset of account.move.lines to export
        :return: string corresponding to the export file content
        """
        raise NotImplementedError

    @api.multi
    def _get_export_filename(self):
        """ Return the export file name

        Can be overridden
        """
        return _(u"account_export_%s.tra") % fields.Date.today()

    @api.multi
    def _send_to_ftp(self):
        """ Send the resulting export (stored in self.binary_export) to the specified ftp server """
        self.ensure_one()
        if not (self.ftp_url and self.ftp_login and self.ftp_password and self.ftp_path):
            raise UserError(_(u"Cannot connect to the FTP : missing parameters"))

        ftp_wizard = self.get_ftp_instance(self.ftp_url, self.ftp_port, self.ftp_login, self.ftp_password)
        dest_ftp = ftp_wizard.get_conn()
        ftp_wizard.mkdir(dest_ftp, self.ftp_path)
        ftp_wizard.chdir(dest_ftp, self.ftp_path)
        ftp_wizard.put(dest_ftp, BytesIO(base64.decodestring(self.binary_export)), self.data_fname)

    @api.multi
    def _onscreen_export(self):
        """ Call a window to present the resulting export to the user """
        return {
            'name': self.display_name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'res_model': self._name,
            'res_id': self.id,
            'context': self.env.context,
            'views': [
                (
                    self.env.ref('account_move_export.account_move_export_wizard_result_form').id,
                    'form'
                ),
            ]
        }
