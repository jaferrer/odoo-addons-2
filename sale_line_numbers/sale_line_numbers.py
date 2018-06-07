# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class SaleOrderLineWithNumber(models.Model):
    _inherit = 'sale.order.line'

    line_no = fields.Char("Line no.", required=True)

    _sql_constraints = [('line_no_unique_by_order', 'unique (order_id, line_no)',
                         _(u"You can not have two lines with same line number in the same sale order."))]

    @api.multi
    def name_get(self):
        if self.env.context.get('display_line_no'):
            return [(rec.id, u"%s - %s" % (rec.order_id.name, rec.line_no)) for rec in self]
        return super(SaleOrderLineWithNumber, self).name_get()
