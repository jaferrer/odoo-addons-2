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

from openerp import models, fields


class ExpeditionByOrderLineProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    sale_id = fields.Many2one('sale.order', string=u"Sale Order", related='sale_line_id.order_id', store=True,
                              readonly=True)

class ExpeditionByOrderLineStockMove(models.Model):
    _inherit = 'stock.move'

    sale_line_id = fields.Many2one('sale.order.line', string=u"Sale Order Line", index=True)
    sale_id = fields.Many2one('sale.order', string=u"Sale Order", related='sale_line_id.order_id', store=True,
                              readonly=True)


class ExpeditionByOrderLineSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    procurement_ids = fields.One2many('procurement.order', 'sale_line_id', readonly=True)
