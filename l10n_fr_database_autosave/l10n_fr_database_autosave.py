# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
import os
from datetime import datetime as dt
from glob import iglob

from openerp import models, fields, api


class DbBackup(models.Model):
    _inherit = 'db.backup'

    @api.multi
    def action_backup(self):
        min_filename = self.filename(dt.now())
        return super(DbBackup, self.with_context(min_filename=min_filename)).action_backup()

    @api.multi
    def cleanup(self):
        result = super(DbBackup, self).cleanup()
        min_filename = self.env.context.get('min_filename')
        if not min_filename:
            return result
        max_filename = self.filename(dt.now())
        for rec in self.filtered(lambda backup: backup.method == 'local'):
            min_path = os.path.join(rec.folder, min_filename)
            max_path = os.path.join(rec.folder, max_filename)
            for total_path in iglob(os.path.join(rec.folder, "*.dump.zip")):
                if total_path >= min_path and total_path <= max_path:
                    self.create_attachment_for_file(total_path)
        return result

    @api.model
    def create_attachment_for_file(self, total_path):
        name = u"Automatic Backup %s" % total_path
        with open(total_path, 'rb') as file:
            content = file.read()
            self.env['ir.attachment'].create({
                'res_name': name,
                'datas_fname': name,
                'name': name,
                'type': 'binary',
                'datas': base64.encodestring(content),
                'protected_attachment': True,
                'database_backup': True,
            })

    @api.multi
    def cleanup_log(self):
        pass


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    database_backup = fields.Boolean(string=u"Database Backup", readonly=True)
