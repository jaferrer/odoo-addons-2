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
    def prepare_line_vals(self, att):
        return {
            'attachment_id': att.id,
            'old_name': att.name,
        }

    @api.model
    def default_get(self, fields_list):
        attachments = self.env['ir.attachment'].search(self.get_attachment_domain())
        return {
            'line_ids': [(0, 0, self.prepare_line_vals(att)) for att in attachments],
        }

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

    @api.multi
    def get_final_name(self):
        self.ensure_one()
        return self.new_name

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
                rec.attachment_id.write({
                    'name': rec.get_final_name(),
                    'fs_name': rec.new_name,
                })
