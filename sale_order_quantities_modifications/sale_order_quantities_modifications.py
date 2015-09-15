# -*- coding: utf8 -*-
#
#    Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class QuantitiesModificationsSaleOrder(models.Model):
    _inherit = 'sale.order'

    order_line = fields.One2many('sale.order.line', 'order_id', readonly=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})


class QuantitiesModificationsSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_uom_qty = fields.Float(readonly=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})

    @api.multi
    def unlink(self):
        for rec in self:
            print 'supperssion ligne', rec
            if rec.procurement_ids:
                print 'suppression procurements', rec.procurement_ids
                rec.procurement_ids.cancel()
                rec.procurement_ids.unlink()
        self.button_cancel()
        return super(QuantitiesModificationsSaleOrderLine, self).unlink()