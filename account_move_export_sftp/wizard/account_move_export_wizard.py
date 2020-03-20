# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class AccountMoveExportWizard(models.TransientModel):
    _inherit = 'account.move.export.wizard'

    @api.model
    def _get_default_key_type(self):
        return self.env['ir.config_parameter'].sudo().get_param('account_move_export_sftp.sftp_key_type', False)

    @api.model
    def _get_default_key(self):
        return self.env['ir.config_parameter'].sudo().get_param('account_move_export_sftp.sftp_key', False)

    key_type = fields.Char(u"Host key type", default=_get_default_key_type)
    key = fields.Char(u"Host key", default=_get_default_key)

    @api.multi
    def get_ftp_instance(self, host, port, username, password):
        """ Create a SFTPWizard instance and return it

        Replace the original function spawning a FTP wizard, with a more secure SFTP wizazrd
        """
        return self.env['sftp.wizard'].create({
            'host': host,
            'port': port or 22,
            'username': username,
            'password': password,
            'key_type': self.key_type,
            'key_str': self.key,
        })
