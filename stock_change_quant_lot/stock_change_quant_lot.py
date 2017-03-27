# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api, exceptions, _


class StockChangeQuantLotStockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.multi
    def change_quants_lots(self):
        group_stock_manager = self.env.ref('stock.group_stock_manager')
        if group_stock_manager not in self.env.user.groups_id:
            raise exceptions.except_orm(_("Error!"), _("You are not allowed to execute this action."))
        products = set([quant.product_id for quant in self])
        if len(products) > 1:
            raise exceptions.except_orm(_("Error!"), _("You have quants of different products: %s. "
                                                       "Please change lots product by product") %
                                        ', '.join([product.display_name for product in products]))
        ctx = self.env.context.copy()
        ctx['default_quant_ids'] = [(6, 0, self.ids)]
        return {
            'name': _("Change quants lots"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.change.quant.lot',
            'target': 'new',
            'context': ctx,
        }


class StockChangeQuantLot(models.TransientModel):
    _name = 'stock.change.quant.lot'

    quant_ids = fields.Many2many('stock.quant', string=u"Quants", readonly=True)
    product_id = fields.Many2one('product.product', related='quant_ids.product_id', readonly=True,
                                 string=u"Product of the lot")
    lot_id = fields.Many2one('stock.production.lot', string=u"New lot")

    @api.multi
    def change_quants_lots(self):
        self.ensure_one()
        if self.quant_ids:
            product = self.quant_ids[0].product_id
            if not self.lot_id:
                self.quant_ids.sudo().write({'lot_id': False})
            elif self.lot_id.product_id != product:
                raise exceptions.except_orm(_("Error!"), _("You are trying to set a quant of product %s to "
                                                           "the lot %s of article %s: this is not possible") %
                                            (product.display_name, self.lot_id.name,
                                             self.lot_id.product_id.display_name))
            else:
                self.quant_ids.sudo().write({'lot_id': self.lot_id.id})
