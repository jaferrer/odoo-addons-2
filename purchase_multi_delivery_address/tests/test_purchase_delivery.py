# -*- coding: utf-8 -*-
# © 2014-2016 Numérigraphe SARL
# © 2016 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.tests.common import TransactionCase


class TestDeliverySingle(TransactionCase):

    def setUp(self):
        super(TestDeliverySingle, self).setUp()
        # Products
        p1 = self.env.ref('product.product_product_15')
        p2 = self.env.ref('product.product_product_25')

        self.po = self.env['purchase.order'].create({
            'partner_id': self.ref('base.res_partner_3'),
            'order_line': [
                (0, 0, {'product_id': p1.id,
                        'product_uom': p1.uom_id.id,
                        'name': p1.name,
                        'price_unit': p1.standard_price,
                        'date_planned': "2017-11-10",
                        'product_qty': 42.0}),
                (0, 0, {'product_id': p2.id,
                        'product_uom': p2.uom_id.id,
                        'name': p2.name,
                        'price_unit': p2.standard_price,
                        'date_planned': "2017-11-10",
                        'product_qty': 12.0}),
                (0, 0, {'product_id': p1.id,
                        'product_uom': p1.uom_id.id,
                        'name': p1.name,
                        'price_unit': p1.standard_price,
                        'date_planned': "2017-11-10",
                        'product_qty': 1.0})]})

    def test_10_check_single_picking(self):
        self.assertEquals(
            len(self.po.picking_ids), 0,
            "There must not be pickings for the PO when draft")
        self.po.button_confirm()
        self.assertEquals(
            len(self.po.picking_ids), 1,
            "There must be 1 picking for the PO when confirmed")
        self.assertEquals(
            self.po.picking_ids[0].partner_id.id, self.ref('base.res_partner_3'),
            "The picking's partner must be the vendor")
        self.assertFalse(
            self.po.picking_ids[0].partner_dest_id.id,
            "The picking's destination address should be empty")
        self.assertEquals(
            self.po.picking_ids[0].picking_type_id.id, self.ref('stock.picking_type_in'),
            "The picking's type must be 'Receipts'")

    def test_20_check_multiple_pickings(self):
        # Change the partner_dest_id of the first line
        self.po.order_line[0].partner_dest_id = self.ref('base.res_partner_2')
        self.assertEquals(
            len(self.po.picking_ids), 0,
            "There must not be pickings for the PO when draft")
        self.po.button_confirm()
        self.assertEquals(
            len(self.po.picking_ids), 2,
            "There must be 2 pickings for the PO when confirmed. %s found"
            % len(self.po.picking_ids))

        sorted_pickings = sorted(self.po.picking_ids, key=lambda x: x.id, reverse=True)
        self.assertEquals(
            sorted_pickings[0].partner_dest_id.id, self.ref('base.res_partner_2'),
            "The first picking partner_dest_id should be the customer")
        self.assertEquals(
            sorted_pickings[0].partner_id.id, self.ref('base.res_partner_3'),
            "The first picking partner_id should be the vendor")
        self.assertEquals(
            sorted_pickings[0].picking_type_id.id, self.ref('stock_dropshipping.picking_type_dropship'),
            "The first picking must be a dropshipping")
        self.assertEquals(
            sorted_pickings[0].location_dest_id.id, self.ref('stock.stock_location_customers'),
            "The first picking must be delivered directly to customer location")
        self.assertEquals(
            sorted_pickings[1].partner_id.id, self.ref('base.res_partner_3'),
            "The second picking must be with partner set to vendor")
        self.assertEquals(
            sorted_pickings[1].picking_type_id.id, self.ref('stock.picking_type_in'),
            "The second picking must be a receipt")
        self.assertEquals(
            sorted_pickings[1].location_dest_id.id, self.ref('stock.stock_location_stock'),
            "The second picking must be delivered to the stock")
        self.assertFalse(
            sorted_pickings[1].partner_dest_id.id, "The picking's destination address should be empty")

    def test_30_check_po_creation_from_proc(self):
        product15 = self.browse_ref('product.product_product_15')
        product15.route_ids = [(4, self.ref('purchase.route_warehouse0_buy'))]
        proc = self.env['procurement.order'].create({
            'name': "Test proc",
            'product_qty': 20,
            'product_id': product15.id,
            'product_uom': self.ref('product.product_uom_unit'),
            'partner_dest_id': self.ref('base.res_partner_2'),
            'location_id': self.ref('stock.stock_location_customers'),
            'rule_id': self.ref('stock_dropshipping.procurement_rule_drop_shipping')
        })
        proc.run()
        po = proc.purchase_id
        self.assertTrue(po)
        self.assertEquals(po.partner_id.id, self.ref('base.res_partner_4'))

        po_line = po.order_line[0]
        self.assertTrue(po_line)
        self.assertEquals(po_line.partner_dest_id.id, self.ref('base.res_partner_2'))
        po.button_confirm()
        pick = po.picking_ids[0]
        self.assertTrue(pick)
        self.assertEquals(
            pick.partner_dest_id.id, self.ref('base.res_partner_2'),
            "The first picking must be for the partner_dest_id")
        self.assertEquals(
            pick.partner_id.id, self.ref('base.res_partner_4'),
            "The first picking partner_id should be the vendor")
        self.assertEquals(
            pick.picking_type_id.id, self.ref('stock_dropshipping.picking_type_dropship'),
            "The first picking must be a dropshipping")
        self.assertEquals(
            pick.location_dest_id.id, self.ref('stock.stock_location_customers'),
            "The first picking must be delivered directly to customer location")

        proc2 = self.env['procurement.order'].create({
            'name': "Test proc 2",
            'product_qty': 100,
            'product_id': product15.id,
            'product_uom': self.ref('product.product_uom_unit'),
            'location_id': self.ref('stock.stock_location_stock'),
        })
        proc2.run()
        po2 = proc2.purchase_id
        self.assertTrue(po2)
        po_line2 = po2.order_line[0]
        self.assertTrue(po_line2)
        self.assertFalse(po_line2.partner_dest_id)
        po2.button_confirm()
        pick2 = po2.picking_ids[0]
        self.assertTrue(pick2)
        self.assertEquals(
            pick2.partner_id.id, self.ref('base.res_partner_4'),
            "The second picking must be with partner set to vendor")
        self.assertFalse(
            pick2.partner_dest_id.id, "The picking's destination address should be empty")
        self.assertEquals(
            pick2.picking_type_id.id, self.ref('stock.picking_type_in'),
            "The second picking must be a receipt")
        self.assertEquals(
            pick2.location_dest_id.id, self.ref('stock.stock_location_stock'),
            "The second picking must be delivered to the stock")
