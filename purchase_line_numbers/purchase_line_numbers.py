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


class ReceptionByOrderStockMove(models.Model):
    _inherit = 'stock.move'
    _order = 'priority desc, date_expected asc, id'


class ReceptionByOrderPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def renumerate_lines(self):
        for rec in self:
            number = 10
            for line in rec.order_line:
                line.line_no = str(number)
                number += 10

    @api.multi
    def do_merge(self):
        result = super(ReceptionByOrderPurchaseOrder, self).do_merge()
        assert len(result.keys()) == 1, "Error: multiple children purchase orders in do_merge result"
        assert isinstance(result.keys()[0], int), "Error, type is not integer: wrong value for id"
        children_po = self.env['purchase.order'].browse(result.keys()[0])
        children_po.renumerate_lines()
        return result


class ReceptionByOrderPurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    line_no = fields.Char("Line no.")

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, "%s - %s - %s" %
                           (rec.order_id.display_name, rec.line_no, rec.product_id.display_name)))
        return result

    @api.model
    def create(self, vals):
        if not vals.get('line_no', False):
            order = self.env['purchase.order'].browse(vals['order_id'])
            list_line_no = []
            for line in order.order_line:
                try:
                    list_line_no.append(int(line.line_no))
                except ValueError:
                    pass
            theo_value = 10 * (1 + len(order.order_line))
            maximum = list_line_no and max(list_line_no) or 0
            if maximum >= theo_value or theo_value in list_line_no:
                theo_value = maximum + 10
            vals['line_no'] = str(theo_value)
        return super(ReceptionByOrderPurchaseOrderLine, self).create(vals)
