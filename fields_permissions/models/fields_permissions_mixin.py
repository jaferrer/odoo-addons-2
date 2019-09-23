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

from odoo import models, api
from odoo.exceptions import AccessError


class FieldPermissionsMixin(models.AbstractModel):
    _name = 'fields.permissions.mixin'
    _description = u"Field Permissions Mixin"

    @api.multi
    def _get_forbidden_fields(self, field_names, perm_type):
        """  Get forbidden fields in a list of fields for the current user and context

         :param field_names: iterable of field names on which we want to know the current user rights
         :param perm_type: str, currently 'perm_read' or 'perm_write', decribing the type of operation that we want
         :return: set of forbidden field names
         :rtype: set
         """
        forbidden_fields = set()
        if self.env.user == self.env.ref('base.user_root'):
            return forbidden_fields
        for field_name in field_names:
            perm_value = getattr(self._fields.get(field_name), perm_type,
                                 getattr(self._fields.get(field_name), 'perm_rw', True))
            if callable(perm_value):
                perm_value = perm_value(self)
            elif isinstance(perm_value, str):
                perm_read_fun = getattr(self, perm_value)
                perm_value = perm_read_fun()
            if not perm_value:
                forbidden_fields.add(field_name)

        return forbidden_fields

    @api.multi
    def _read_from_database(self, field_names, inherited_field_names=None):
        """ Call BaseModel._read_from_database and obfuscates fields on which the current user lack permission

        Inspired by the _read_from_database override in res.users
        """
        inherited_field_names = inherited_field_names or []
        super(FieldPermissionsMixin, self)._read_from_database(field_names, inherited_field_names)

        for rec in self:
            forbidden_fields = rec._get_forbidden_fields(field_names + inherited_field_names, 'perm_read')
            for field_name in forbidden_fields:
                try:
                    field_type = rec._fields.get(field_name).type
                    if field_type == 'many2one':
                        blank = self.env[rec._fields.get(field_name).comodel_name]
                    elif field_type.endswith('2many'):
                        blank = []
                    else:
                        blank = False
                    rec._cache[field_name]
                    rec._cache[field_name] = blank
                except KeyError:
                    pass

    @api.multi
    def _write(self, vals):
        forbidden_fields = self._get_forbidden_fields(vals.keys(), 'perm_write')
        if forbidden_fields:
            raise AccessError(u"Sorry, you are not allowed to write this ressource (fields %s on %s)" %
                              (', '.join(forbidden_fields), self._name))
        return super(FieldPermissionsMixin, self)._write(vals)
