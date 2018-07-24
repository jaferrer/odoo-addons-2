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

from openerp import fields
from openerp.tests import common


class TestPurchaseReceptionUpdatePrices(common.TransactionCase):
    def setUp(self):
        super(TestPurchaseReceptionUpdatePrices, self).setUp()
        self.product = self.env['product.product'].search([('type', '=', 'product')], limit=1)
        self.assertTrue(self.product)
        self.supplier = self.env['res.partner'].search([('supplier', '=', True)], limit=1)
        self.assertTrue(self.supplier)
        self.pricelist = self.env['product.pricelist'].search([], limit=1)
        self.assertTrue(self.pricelist)
        self.location = self.browse_ref('stock.stock_location_stock')
        self.eur = self.browse_ref('base.EUR')
        self.usd = self.browse_ref('base.USD')
        self.main_company = self.browse_ref('base.main_company')
        self.main_company.currency_id = self.eur
        self.usd.rate_ids.unlink()
        self.env['res.currency.rate'].create({'currency_id': self.usd.id,
                                              'name': '2010-01-01 00:00:00',
                                              'rate': 0.5})
        self.eur.rate_ids.unlink()
        self.env['res.currency.rate'].create({'currency_id': self.eur.id,
                                              'name': '2010-01-01 00:00:00',
                                              'rate': 1})

    def test_10_reception_update_prices(self):
        order = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'location_id': self.location.id,
            'pricelist_id': self.pricelist.id,
            'currency_id': self.usd.id,
            'company_id': self.main_company.id,
        })
        line = self.env['purchase.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'date_planned': fields.Datetime.now(),
            'name': "Test Line",
            'price_unit': 1,
            'product_qty': 1,
            'product_uom': self.product.uom_po_id.id
        })
        order.signal_workflow('purchase_confirm')
        self.assertEqual(order.state, 'approved')
        move = line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.price_unit, 2)

        self.env['res.currency.rate'].create({'currency_id': self.usd.id,
                                              'name': '2010-01-02 00:00:00',
                                              'rate': 2})
        self.env['currency.rate.update.service']._run_currency_update()
        move.action_done()
        self.assertEqual(move.price_unit, 0.5)
        moved_quant = move.quant_ids
        self.assertEqual(len(moved_quant), 1)
        self.assertEqual(moved_quant.cost, 0.5)
