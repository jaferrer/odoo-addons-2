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

from odoo import models, api, _


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _read_group_format_result(self, data, annotated_groupbys, groupby, domain):
        data = super(Base, self)._read_group_format_result(data, annotated_groupbys, groupby, domain)
        for gb in annotated_groupbys:
            ftype = gb['type']
            value = data[gb['groupby']]
            if ftype == 'boolean':
                data[gb['groupby']] = value and _(u"yes") or _(u"no")
        return data
