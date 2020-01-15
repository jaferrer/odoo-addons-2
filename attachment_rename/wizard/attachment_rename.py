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
import os

from odoo import models, fields, api


class IrAttachmentRename(models.TransientModel):
    _name = 'ir.attachment.rename'

    line_ids = fields.One2many('ir.attachment.rename.line', 'renamer_id')

    def get_attachment_domain(self):
        return [
            ('res_model', '=', self._context.get('active_model')),
            ('res_id', '=', self._context.get('active_id'))
        ]

    @api.model
    def default_get(self, fields_list):
        line_ids = []
        res = {}
        attachment_domain = self.get_attachment_domain()
        for att in self.env['ir.attachment'].search(attachment_domain):
            att_record = self.env[att.res_model].browse(att.res_id)
            folder_name = att_record._name == 'folder' and att_record.name or att_record.folder_id.name
            line_ids.append((0, 0, {
                'folder_name': folder_name,
                'attachment_id': att.id,
                'old_name': att.name,
                'prefix_folder_name': True,
            }))

        res['line_ids'] = line_ids
        return res

    @api.multi
    def action_change_all_name(self):
        self.ensure_one()
        self.line_ids.change_name()


class IrAttachmentRenameLine(models.TransientModel):
    _name = 'ir.attachment.rename.line'

    renamer_id = fields.Many2one('ir.attachment.rename', required=True)
    attachment_id = fields.Many2one('ir.attachment', required=True)
    old_name = fields.Char(u"Nom actuel du document", related='attachment_id.name', readonly=True, required=True)
    new_name = fields.Char(u"Nouveau nom")
    folder_name = fields.Char(u"Nom du dossier")
    prefix_folder_name = fields.Boolean(u"Préfixer par le numéro de dossier", default=True)

    @api.multi
    def change_name(self):
        for rec in self:
            if rec.new_name:
                # Permet de garder l'extension si elle a été oubliée
                new_filename, new_extension = os.path.splitext(rec.new_name)
                _, old_extension = os.path.splitext(rec.old_name)
                if not new_extension:
                    rec.new_name += old_extension
                elif new_extension != old_extension:
                    rec.new_name = new_filename + old_extension

                final_name = rec.prefix_folder_name and u"-".join(
                    [rec.folder_name, rec.new_name]) or rec.new_name

                rec.attachment_id.write({
                    'name': final_name,
                    'fs_name': rec.new_name,
                })
