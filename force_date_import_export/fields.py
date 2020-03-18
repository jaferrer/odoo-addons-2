# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from openerp.tools import ustr


def convert_to_export(self, value, env):
    if not value:
        return ''
    if self._attrs.get('export_import_date'):
        return fields.Date.from_string(value) if env.context.get('export_raw_data') \
            else fields.Date.to_string(self.from_string(value))
    return self.from_string(value) if env.context.get('export_raw_data') else ustr(value)


fields.Datetime.convert_to_export = convert_to_export


class ForceDateImport(models.Model):
    _inherit = 'ir.fields.converter'

    @api.model
    def _str_to_datetime(self, model, field, value):
        if field._attrs.get('export_import_date'):
            value = fields.Datetime.to_string(fields.Datetime.from_string(value))

        return super(ForceDateImport, self)._str_to_datetime(model, field, value)
