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


class IrAttachmentRename(models.TransientModel):
    _name = 'ir.attachment.rename'

    line_ids = fields.One2many('ir.attachment.rename.line', 'renamer_id')

    @api.model
    def default_get(self, fields_list):
        line_ids = []
        res = {}
        attachment_domain = [
            ('res_model', '=', self._context.get('active_model')),
            ('res_id', '=', self._context.get('active_id'))
        ]
        for att in self.env['ir.attachment'].search(attachment_domain):
            line_ids.append((0, 0, {
                'attachment_id': att.id,
                'old_name': att.name,
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

    @api.multi
    def change_name(self):
        for rec in self:
            if rec.new_name:
                rec.attachment_id.write({
                    'name': rec.new_name,
                    'fs_name': rec.new_name,
                })
