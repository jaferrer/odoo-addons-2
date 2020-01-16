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

from openerp import models, api, exceptions, _
from openerp.tools import float_compare


class StockQuant(models.Model):
    _inherit = "stock.move"

    @api.model
    def create(self, vals):
        uom_id = vals.get('product_uom')
        product_id = vals.get('product_id')
        move_qty = float(vals.get('product_uom_qty', 0))
        uom = uom_id and self.env['product.uom'].search([('id', '=', uom_id)]) or \
            self.env['product.product'].search([('id', '=', product_id)]).uom_id or False
        negative_move = uom and float_compare(move_qty, 0.0, precision_rounding=uom.rounding) <= 0 or move_qty <= 0
        if negative_move:
            raise exceptions.except_orm(_(u"Error!"), _(u"You are not allowed to create a negative or null move."))
        return super(StockQuant, self).create(vals)

    @api.multi
    def write(self, vals):
        for rec in self:
            uom_id = vals.get('product_uom', rec.product_uom.id)
            product_id = vals.get('product_id', rec.product_id.id)
            move_qty = float(vals.get('product_uom_qty', rec.product_uom_qty or 0))
            uom = uom_id and self.env['product.uom'].search([('id', '=', uom_id)]) or \
                self.env['product.product'].search([('id', '=', product_id)]).uom_id or False
            negative_move = uom and float_compare(move_qty, 0.0, precision_rounding=uom.rounding) <= 0 or move_qty <= 0
            if negative_move and not self.env.context.get('allow_move_null_qty', False):
                raise exceptions.except_orm(_(u"Error!"), _(u"You are not allowed to create a negative or null move."))
        return super(StockQuant, self).write(vals)
