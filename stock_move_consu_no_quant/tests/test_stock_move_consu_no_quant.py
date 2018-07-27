# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class TestStockAutoMove(common.TransactionCase):

    def setUp(self):
        super(TestStockAutoMove, self).setUp()
        self.picking_obj = self.env['stock.picking']
        self.move_obj = self.env['stock.move']
        self.inventory_obj = self.env['stock.inventory']
        self.quant_obj = self.env['stock.quant']

        self.partner = self.browse_ref("base.res_partner_6")

        self.location_customer = self.browse_ref("stock.stock_location_7")
        self.location_stock = self.browse_ref("stock.stock_location_components")
        self.location_stock2 = self.browse_ref("stock.stock_location_14")

        self.internal_picking_type = self.browse_ref("stock.picking_type_internal")
        self.in_picking_type = self.browse_ref("stock.picking_type_in")
        self.out_picking_type = self.browse_ref("stock.picking_type_out")

        self.product_uom_unit = self.browse_ref('product.product_uom_unit')

        self.product_consu = self.browse_ref('product.product_product_42')
        self.product_service = self.browse_ref('product.product_product_2')
        self.product_stock = self.browse_ref('product.product_product_6')

    def create_picking(self, picking_type, location_source, location_dest):
        vals = {
            'picking_type_id': picking_type.id,
            'origin': picking_type.name + ' your_company warehouse',
            'partner_id': self.partner.id
        }
        picking = self.picking_obj.create(vals)

        vals_product_stock = {
            'name': u"Move 1",
            'product_id': self.product_stock.id,
            'product_uom': self.product_stock.uom_id.id,
            'product_uom_qty': 5,
            'picking_id': picking.id,
            'picking_type_id': picking_type.id,
            'location_id': location_source.id,
            'location_dest_id': location_dest.id,
        }
        self.move_obj.create(vals_product_stock)
        vals_product_consu = {
            'name': u"Move 2",
            'product_id': self.product_consu.id,
            'product_uom': self.product_consu.uom_id.id,
            'product_uom_qty': 3,
            'picking_id': picking.id,
            'picking_type_id': picking_type.id,
            'location_id': location_source.id,
            'location_dest_id': location_dest.id,
        }
        self.move_obj.create(vals_product_consu)
        return picking

    def test_10_picking_intern_to_intern(self):
        picking = self.create_picking(self.internal_picking_type, self.location_stock, self.location_stock2)
        picking.action_confirm()
        picking.action_assign()
        transfert = picking.do_enter_transfer_details()
        transfert = self.env['stock.transfer_details'].browse(transfert['res_id'])
        transfert.do_detailed_transfer()

        #     Test start here

        picking = self.picking_obj.search([('id', '=', picking.id)])
        self.assertEquals('done', picking.state)

        inventory_stock1 = self.inventory_obj.search(
            [('filter', '=', 'product'), ('product_id', '=', self.product_consu.id),
             ('location_id', '=', self.location_stock.id)])

        self.assert_inventory(inventory_stock1, self.location_stock)

        inventory_stock2 = self.inventory_obj.search(
            [('filter', '=', 'product'), ('product_id', '=', self.product_consu.id),
             ('location_id', '=', self.location_stock2.id)])

        self.assert_inventory(inventory_stock2, self.location_stock2)

        quant_stock = self.quant_obj.search([('product_id', '=', self.product_consu.id),
                                             ('location_id', '=', self.location_stock.id)])
        self.assertFalse(quant_stock)

    def test_20_picking_intern_to_extern(self):
        picking = self.create_picking(self.out_picking_type, self.location_stock, self.location_customer)
        picking.action_confirm()
        picking.action_assign()
        transfert = picking.do_enter_transfer_details()
        transfert = self.env['stock.transfer_details'].browse(transfert['res_id'])
        transfert.do_detailed_transfer()

        #     Test start here

        picking = self.picking_obj.search([('id', '=', picking.id)])
        self.assertEquals('done', picking.state)

        inventory = self.inventory_obj.search(
            [('filter', '=', 'product'), ('product_id', '=', self.product_consu.id)])

        self.assert_inventory(inventory, self.location_stock)

        quant_stock = self.quant_obj.search([('product_id', '=', self.product_consu.id),
                                             ('location_id', '=', self.location_stock.id)])
        self.assertFalse(quant_stock)

    def test_30_picking_extern_to_internal(self):
        picking = self.create_picking(self.in_picking_type, self.location_customer, self.location_stock)
        picking.action_confirm()
        picking.action_assign()
        transfert = picking.do_enter_transfer_details()
        transfert = self.env['stock.transfer_details'].browse(transfert['res_id'])
        transfert.do_detailed_transfer()

        #     Test start here

        picking = self.picking_obj.search([('id', '=', picking.id)])
        self.assertEquals('done', picking.state)

        inventory = self.inventory_obj.search(
            [('filter', '=', 'product'), ('product_id', '=', self.product_consu.id)])

        self.assert_inventory(inventory, self.location_stock)

        quant_stock = self.quant_obj.search([('product_id', '=', self.product_consu.id),
                                             ('location_id', '=', self.location_stock.id)])
        self.assertFalse(quant_stock)

    def assert_inventory(self, inventory, loc):
        self.assertTrue(inventory)
        self.assertEquals(1, len(inventory.ids))
        self.assertEquals('done', inventory.state)
        self.assertEquals(1, len(inventory.line_ids.ids))
        self.assertEquals(self.product_consu, inventory.line_ids[0].product_id)
        self.assertEquals(loc, inventory.line_ids[0].location_id)
        self.assertEquals(0, inventory.line_ids[0].product_qty)
