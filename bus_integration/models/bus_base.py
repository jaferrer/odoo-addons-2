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

from openerp import models, fields, api, _


class BusBase(models.Model):
    _name = 'bus.base'

    name = fields.Char(u"Name")
    bus_username = fields.Char(u"BUS user name", required=True)
    active = fields.Boolean(u"Active", default=True)
    url = fields.Char(string=u"Url")

    _sql_constraints = [('uq_constraint_bus_mapping', 'UNIQUE(bus_username)',
                         _(u'bus synchronisation requires unique values for : %s') % 'bus_username')]

    @api.multi
    def name_get(self):
        return [(rec.id, rec.bus_username.replace("base_", "") .upper() or "") for rec in self]
