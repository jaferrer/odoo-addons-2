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
from openerp import models, api, _


class StockTransfertDetails(models.TransientModel):
    _inherit = 'stock.transfer_details'

    @api.one
    def do_detailed_transfer(self):
        res = super(StockTransfertDetails, self).do_detailed_transfer()
        for item in self.item_ids:
            if item.product_id.type == 'consu':
                self.delete_quant_product_consu(item)
        return res

    @api.multi
    def delete_quant_product_consu(self, item):
        invetory = self.env['stock.inventory']
        for vals in item.create_inventory_data().values():
            invetory |= self.env['stock.inventory'].create(vals)
        invetory.auto_execute()


class StockTransferDetailsItems(models.TransientModel):
    _inherit = 'stock.transfer_details_items'

    @api.multi
    def create_inventory_data(self):
        res = {}
        for rec in self:
            pick = rec.transfer_id.picking_id
            if rec.sourceloc_id.usage in ('internal', 'transit'):
                res[rec.sourceloc_id.id] = {
                    'name': _(u"Inventory of Consumable product %s from %s for the location %s" %
                              (rec.product_id.name, pick.name, rec.sourceloc_id.name)),
                    'location_id': rec.sourceloc_id.id,
                    'filter': 'product',
                    'company_id': pick.company_id.id,
                    'product_id': rec.product_id.id
                }
            if rec.destinationloc_id.usage in ('internal', 'transit'):
                res[rec.destinationloc_id.id] = {
                    'name': _(u"Inventory of Consumable product %s from %s for the location %s" %
                              (rec.product_id.name, pick.name, rec.destinationloc_id.name)),
                    'location_id': rec.destinationloc_id.id,
                    'filter': 'product',
                    'company_id': pick.company_id.id,
                    'product_id': rec.product_id.id

                }
        return res


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    @api.multi
    def auto_execute(self):
        self.prepare_inventory()
        for rec in self:
            if len(rec.line_ids.ids) == 0:
                self.env['stock.inventory.line'].create(rec.prepare_line_data())
            rec.reset_real_qty()
        self.action_done()

    def prepare_line_data(self):
        self.ensure_one()
        return {
            'product_id': self.product_id.id,
            'location_id': self.location_id.id,
            'product_uom_id': self.product_id.product_uom_id.id,
            'product_qty': 0,
            'inventory_id': self.id,
        }
