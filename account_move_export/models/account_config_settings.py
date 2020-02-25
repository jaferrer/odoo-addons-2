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

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


class AccountConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    export_mode = fields.Selection([
        ('manual', u"Manual"),
        ('auto', u"Automatic, on FTP")
    ])
    export_line_selection = fields.Selection([
        ('bounded', u"From date to date"),
        ('not_exported', u"Lines not previously exported"),
    ], u"Line selection", default='not_exported')
    export_journal_ids = fields.Many2many('account.journal', string=u"Account journals")
    export_date_from = fields.Date(u"From")
    export_date_to = fields.Date(u"To")
    export_group_by_account = fields.Boolean(u"Group by account")

    export_ftp_url = fields.Char(u"FTP URL")
    export_ftp_login = fields.Char(u"FTP login")
    export_ftp_password = fields.Char(u"FTP password")
    export_ftp_path = fields.Char(u"FTP path")
    export_cron_id = fields.Many2one('ir.cron', u"Export cron", readonly=True)

    @api.model
    def get_values(self):
        res = super(AccountConfigSettings, self).get_values()
        res.update(
            export_mode=self.env.ref('account_move_export.account_move_export_cron').active and 'auto' or 'manual',
            export_journal_ids=safe_eval(
                self.env['ir.config_parameter'].sudo().get_param('account_move_export.export_journal_ids', '[]')),
            export_line_selection=self.env['ir.config_parameter'].sudo().get_param(
                'account_move_export.export_line_selection'),
            export_date_from=self.env['ir.config_parameter'].sudo().get_param('account_move_export.export_date_from'),
            export_date_to=self.env['ir.config_parameter'].sudo().get_param('account_move_export.export_date_to'),
            export_ftp_url=self.env['ir.config_parameter'].sudo().get_param('account_move_export.export_ftp_url'),
            export_ftp_login=self.env['ir.config_parameter'].sudo().get_param('account_move_export.export_ftp_login'),
            export_ftp_password=self.env['ir.config_parameter'].sudo().get_param(
                'account_move_export.export_ftp_password'),
            export_ftp_path=self.env['ir.config_parameter'].sudo().get_param('account_move_export.export_ftp_path'),
            export_group_by_account=safe_eval(self.env['ir.config_parameter'].sudo().get_param(
                'account_move_export.export_group_by_account', 'False')),
        )
        return res

    def set_values(self):
        super(AccountConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('account_move_export.export_line_selection',
                                                         self.export_line_selection)
        self.env['ir.config_parameter'].sudo().set_param('account_move_export.export_journal_ids',
                                                         str(self.export_journal_ids.ids))
        self.env['ir.config_parameter'].sudo().set_param('account_move_export.export_date_from', self.export_date_from)
        self.env['ir.config_parameter'].sudo().set_param('account_move_export.export_date_to', self.export_date_to)
        self.env['ir.config_parameter'].sudo().set_param('account_move_export.export_group_by_account',
                                                         str(self.export_group_by_account))
        self.env['ir.config_parameter'].sudo().set_param('account_move_export.export_ftp_url', self.export_ftp_url)
        self.env['ir.config_parameter'].sudo().set_param('account_move_export.export_ftp_login', self.export_ftp_login)
        self.env['ir.config_parameter'].sudo().set_param('account_move_export.export_ftp_password',
                                                         self.export_ftp_password)
        self.env['ir.config_parameter'].sudo().set_param('account_move_export.export_ftp_path', self.export_ftp_path)
