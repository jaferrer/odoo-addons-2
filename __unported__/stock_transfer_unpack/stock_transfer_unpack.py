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


class StockTransferDetailsItems(models.TransientModel):
    _inherit = "stock.transfer_details_items"

    @api.multi
    def unpack(self):
        """Unpacks the current pack if any"""
        self.ensure_one()
        transfer = self.transfer_id
        if self.package_id and not self.product_id:
            quants = self.package_id.quant_ids
            products = quants.mapped(lambda q: q.product_id)
            packs = self.package_id.children_ids
            datas = []
            for product in products:
                qty = sum([q.qty for q in quants if q.product_id == product])
                datas.append({
                    'product_id': product.id,
                    'product_uom_id': product.uom_id.id,
                    'quantity': qty,
                    'resultpackage_id': False,
                })
            for pack in packs:
                datas.append({
                    'package_id': pack.id,
                    'product_id': False,
                    'product_uom_id': False,
                    'quantity': 1.0,
                    'resultpackage_id': False,
                })
            if len(datas) >= 1:
                # We first modify ourselves not to get "record not correctly loaded" error
                self.with_context(no_recompute=True).write(datas[0])
                # We create new lines for the others
                for data in datas[1:]:
                    data['packop_id'] = False
                    self.with_context(no_recompute=True).copy(data)

        return transfer.wizard_view()
    
    
class stock_product_packop_line(models.Model):
    _inherit = 'stock.pack.operation'

    @api.multi
    def unpack(self):
        """Unpacks the current pack if any"""
        self.ensure_one()
        if self.package_id and not self.product_id:
            quants = self.package_id.quant_ids
            products = quants.mapped(lambda q: q.product_id)
            packs = self.package_id.children_ids
            datas = []
            for product in products:
                qty = sum([q.qty for q in quants if q.product_id == product])
                datas.append({
                    'product_id': product.id,
                    'product_uom_id': product.uom_id.id,
                    'product_qty': qty,
                    'result_package_id': False,
                })
            for pack in packs:
                datas.append({
                    'package_id': pack.id,
                    'product_id': False,
                    'product_uom_id': False,
                    'product_qty': 1.0,
                    'result_package_id': False,
                })
            if len(datas) >= 1:
                # We first modify ourselves not to get "record not correctly loaded" error
                self.with_context(no_recompute=True).write(datas[0])
                # We create new lines for the others
                for data in datas[1:]:
                    data['packop_id'] = False
                    self.with_context(no_recompute=True).copy(data)


