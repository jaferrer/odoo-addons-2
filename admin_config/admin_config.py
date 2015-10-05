# -*- coding: utf8 -*-
#
#    Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api


class IrTranslationImproved(models.Model):
    _inherit = 'ir.translation'

    module_sequence = fields.Integer(string="Sequence", compute='_compute_sequence')

    @api.multi
    def _compute_sequence(self):
        for rec in self:
            module_sequence = False
            if rec.module:
                modules = self.env['ir.module.module'].search([('name', '=', rec.module)])
                if len(modules) == 1:
                    module_sequence = modules[0].sequence
            rec.module_sequence = module_sequence

    @api.multi
    def delete_field_translations(self):
        for rec in self:
            print 'delete', rec, rec.name
            print self.env['ir.translation'].search([('name', '=', rec.name)])
            self.env['ir.translation'].search([('name', '=', rec.name)]).unlink()
