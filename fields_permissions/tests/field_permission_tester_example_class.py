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

from odoo import api, fields, models


class FieldPermissionsTester(models.Model):
    _inherit = ['fields.permissions.mixin']
    _name = 'fields.permissions.tester'

    standard_field = fields.Integer(default=42)
    boolean_forbidden_field = fields.Integer(default=42, perm_read=False, perm_write=False)
    boolean_allowed_field = fields.Integer(default=42, perm_read=True, perm_write=True)
    function_secured_field = fields.Integer(
        default=42,
        perm_read=lambda self: self.env.context.get('allowed_to_read_the_field'),
        perm_write=lambda self: self.env.context.get('allowed_to_write_the_field')
    )
    key_to_method_secured_field = fields.Boolean()
    method_secured_field = fields.Integer(
        default=42,
        perm_read='_perm_read_method_secured_field',
        perm_write='_perm_write_method_secured_field'
    )

    @api.multi
    def _perm_read_method_secured_field(self):
        self.ensure_one()
        return self.key_to_method_secured_field and self.env.context.get('allowed_to_read_the_field')

    @api.multi
    def _perm_write_method_secured_field(self):
        self.ensure_one()
        return self.key_to_method_secured_field and self.env.context.get('allowed_to_write_the_field')
