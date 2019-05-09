# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api


class Model(models.Model):
    _inherit = 'ir.model'

    @api.multi
    def name_get(self):
        if not self.env.context.get('display_short_name', False):
            return super(Model, self).name_get()
        result = []
        for rec in self:
            result.append((rec.id, rec.model))
        return result


class BusIrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    @api.multi
    def name_get(self):
        if self.env.context.get('display_technical_field_names'):
            return [(rec.id, rec.name) for rec in self]
        return super(BusIrModelFields, self).name_get()
