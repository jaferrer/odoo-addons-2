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

from openerp import models, fields, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    table_name = fields.Char(string=u"Table", related="table_id.name", readonly=True)

    # Custom Section
    @api.model
    def search_read_orders(self, query, fields = []):
        condition = [
            ('state', '=', 'draft'),
            ('statement_ids', '=', False),
            '|',
            ('name', 'ilike', query),
            ('partner_id', 'ilike', query)
        ]
        fields = ['name', 'partner_id', 'amount_total', 'table_name'] + fields
        return self.search_read(condition, fields, limit=10)