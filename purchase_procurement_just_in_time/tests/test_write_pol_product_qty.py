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

from openerp.tests import common


class TestWritePolProduct(common.TransactionCase):

    def setUp(self):
        super(TestWritePolProduct, self).setUp()
        self.supplier = self.browse_ref('purchase_procurement_just_in_time.supplier1')
        self.env['product.supplierinfo'].search([('name', '=', self.supplier.id)]).write({'min_qty': 1})
        self.product1 = self.browse_ref('purchase_procurement_just_in_time.product1')
        self.product2 = self.browse_ref('purchase_procurement_just_in_time.product2')
        self.product3 = self.browse_ref('purchase_procurement_just_in_time.product3')
        self.unit = self.browse_ref('product.product_uom_unit')
        self.uom_couple = self.browse_ref('purchase_procurement_just_in_time.uom_couple')
        self.location_a = self.browse_ref('purchase_procurement_just_in_time.stock_location_a')
        self.uom_four = self.browse_ref('purchase_procurement_just_in_time.uom_four')
        self.order_1 = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'location_id': self.location_a.id,
            'pricelist_id': self.ref('purchase.list0')

        })
        self.order_1_line_1 = self.env['purchase.order.line'].create({
            'name': "POL 1 1",
            'line_no': '1',
            'product_id': self.product1.id,
            'product_qty': 10,
            "price_unit": 1.0,
            'product_uom': self.unit.id,
            'order_id': self.order_1.id,
            'covering_state': 'coverage_computed',
            'covering_date': '3003-09-14 17:00:00',
            'date_planned': '3003-09-14 17:00:00',
        })
        self.order_1_line_2 = self.env['purchase.order.line'].create({
            'name': "POL 1 2",
            'line_no': '1',
            'product_id': self.product1.id,
            'product_qty': 10,
            "price_unit": 1.0,
            'product_uom': self.uom_couple.id,
            'order_id': self.order_1.id,
            'covering_state': 'coverage_computed',
            'covering_date': '3003-09-14 17:00:00',
            'date_planned': '3003-09-14 17:00:00',
        })
        self.order_1_line_3 = self.env['purchase.order.line'].create({
            'name': "POL 1 3",
            'line_no': '1',
            'product_id': self.product2.id,
            'product_qty': 10,
            "price_unit": 1.0,
            'product_uom': self.unit.id,
            'order_id': self.order_1.id,
            'covering_state': 'coverage_computed',
            'covering_date': '3003-09-14 17:00:00',
            'date_planned': '3003-09-14 17:00:00',
        })
        self.order_2 = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'location_id': self.location_a.id,
            'pricelist_id': self.ref('purchase.list0')
        })
        self.order_2_line_1 = self.env['purchase.order.line'].create({
            'name': "POL 2 1",
            'line_no': '1',
            'product_id': self.product1.id,
            'product_qty': 10,
            "price_unit": 1.0,
            'product_uom': self.unit.id,
            'order_id': self.order_2.id,
            'covering_state': 'coverage_computed',
            'covering_date': '3003-09-14 17:00:00',
            'date_planned': '3003-09-14 17:00:00',
        })
        self.order_2_line_2 = self.env['purchase.order.line'].create({
            'name': "POL 2 2",
            'line_no': '1',
            'product_id': self.product2.id,
            'product_qty': 10,
            "price_unit": 1.0,
            'product_uom': self.uom_couple.id,
            'order_id': self.order_2.id,
            'covering_state': 'coverage_computed',
            'covering_date': '3003-09-14 17:00:00',
            'date_planned': '3003-09-14 17:00:00',
        })
        self.order_2_line_3 = self.env['purchase.order.line'].create({
            'name': "POL 2 3",
            'line_no': '1',
            'product_id': self.product3.id,
            'product_qty': 10,
            "price_unit": 1.0,
            'product_uom': self.unit.id,
            'order_id': self.order_2.id,
            'covering_state': 'coverage_computed',
            'covering_date': '3003-09-14 17:00:00',
            'date_planned': '3003-09-14 17:00:00',
        })

    def test_1(self):
        """Je change Uniquement le product_qty d'une ligne

        Je verifie :

        Que toute les lignes de PO qui on le même article sont bien changé sans débordement sur d'autre POL"""
        self.order_1_line_1.product_qty = 20
        self.assert_line_reset(self.order_1_line_1)
        self.assert_line_reset(self.order_1_line_2)
        self.assert_line_not_changed(self.order_1_line_3)
        self.assert_line_not_changed(self.order_2_line_1)
        self.assert_line_not_changed(self.order_2_line_2)
        self.assert_line_not_changed(self.order_2_line_3)

    def test_2(self):
        """Je change Uniquement le product_uom d'une ligne

        Je verifie :

        Que toute les lignes de PO qui on le même article sont bien changé sans débordement sur d'autre POL"""
        self.order_1_line_1.product_uom = self.uom_four

        self.assert_line_reset(self.order_1_line_1)
        self.assert_line_reset(self.order_1_line_2)
        self.assert_line_not_changed(self.order_1_line_3)

        self.assert_line_not_changed(self.order_2_line_1)
        self.assert_line_not_changed(self.order_2_line_2)
        self.assert_line_not_changed(self.order_2_line_3)

    def test_3(self):
        """Je change Uniquement le product_qty de 2 lignes de la même PO

        Je verifie :

        Que toute les lignes de PO qui on le même article sont bien changé sans débordement sur d'autre POL"""
        lines = self.order_2_line_1 + self.order_2_line_2
        lines.write({'product_qty': 15})

        self.assert_line_not_changed(self.order_1_line_1)
        self.assert_line_not_changed(self.order_1_line_2)
        self.assert_line_not_changed(self.order_1_line_3)

        self.assert_line_reset(self.order_2_line_1)
        self.assert_line_reset(self.order_2_line_2)
        self.assert_line_not_changed(self.order_2_line_3)

    def test_4(self):
        """Je change le product_qty de 2 lignes de 2 PO differente

        Je verifie :

        Que toute les lignes de PO qui on le même article sont bien changé sans débordement sur l'autre PO de la ligne 2"""
        lines = self.order_1_line_1 + self.order_2_line_2
        lines.write({'product_qty': 15})

        self.assert_line_reset(self.order_1_line_1)
        self.assert_line_reset(self.order_1_line_2)
        self.assert_line_not_changed(self.order_1_line_3)

        self.assert_line_not_changed(self.order_2_line_1)
        self.assert_line_reset(self.order_2_line_2)
        self.assert_line_not_changed(self.order_2_line_3)

    def test_5(self):
        """Je change le product_qty de 2 lignes de 2 PO differentes en changeant PO le la premiere ligne
        Je verifie :

        Toutes les lignes de la PO d'origine de la première ligne possedant le même article sont changées

        Toutes les ligne de la nouvelle PO possedant le même article sont changées"""
        lines = self.order_1_line_1 + self.order_2_line_2
        lines.write({'product_qty': 15, 'order_id': self.order_2.id})

        self.assert_line_reset(self.order_1_line_1)
        self.assert_line_reset(self.order_1_line_2)
        self.assert_line_not_changed(self.order_1_line_3)

        self.assert_line_reset(self.order_2_line_1)
        self.assert_line_reset(self.order_2_line_2)
        self.assert_line_not_changed(self.order_2_line_3)

    def test_6(self):
        """Je change de PO une ligne sans changé la quantité

        Je verifie :

        Toutes les lignes de la PO d'origine possedant le même article sont changées

        Toutes les ligne de la nouvelle PO possedant le même article sont changées"""
        self.order_1_line_2.write({'order_id': self.order_2.id})

        self.assert_line_reset(self.order_1_line_1)
        self.assert_line_reset(self.order_1_line_2)
        self.assert_line_not_changed(self.order_1_line_3)

        self.assert_line_reset(self.order_2_line_1)
        self.assert_line_not_changed(self.order_2_line_2)
        self.assert_line_not_changed(self.order_2_line_3)

    def test_7(self):
        """Je change de PO une ligne sans changé la quantité

        Je verifie :

        Toutes les lignes de la PO d'origine possedant le même article sont changées

        Toutes les ligne de la nouvelle PO possedant le même article sont changées"""
        self.order_2_line_2.write({'product_id': self.product1.id})

        self.assert_line_not_changed(self.order_1_line_1)
        self.assert_line_not_changed(self.order_1_line_2)
        self.assert_line_not_changed(self.order_1_line_3)

        self.assert_line_reset(self.order_2_line_1)
        self.assert_line_reset(self.order_2_line_2)
        self.assert_line_not_changed(self.order_2_line_3)

    def assert_line_reset(self, line):
        self.assertEqual('unknow_coverage', line.covering_state)
        self.assertFalse(line.covering_date)

    def assert_line_not_changed(self, line):
        self.assertEqual('coverage_computed', line.covering_state)
        self.assertEqual('3003-09-14 17:00:00', line.covering_date)
