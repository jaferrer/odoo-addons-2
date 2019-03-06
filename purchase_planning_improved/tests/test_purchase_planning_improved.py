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

from datetime import datetime

from openerp.tests import common


class TestPurchasePlanningImproved(common.TransactionCase):
    def setUp(self):
        super(TestPurchasePlanningImproved, self).setUp()
        self.test_product = self.browse_ref("stock_working_days.product_test_product")
        self.location_a = self.browse_ref("stock_working_days.stock_location_a")
        self.location_b = self.browse_ref("stock_working_days.stock_location_b")
        self.test_supplier = self.browse_ref("purchase_working_days.test_supplier")
        self.location_c = self.browse_ref("stock_planning_improved.stock_location_c")
        self.location_inv = self.browse_ref("stock.location_inventory")
        self.product_uom_unit_id = self.ref("product.product_uom_unit")
        self.env['product.template'].update_seller_ids()

    def create_move_out_corresponding_to_procs(self):
        self.env['stock.move'].search([('origin', '=', 'to_remove'),
                                       ('state', 'not in', ['cancel', 'done'])]).action_cancel()
        for proc in self.env['procurement.order'].search([('state', 'not in', ['done', 'cancel']),
                                                          ('location_id', '=', self.location_a.id),
                                                          ('rule_id.action', '=', 'buy')]):
            if not proc.move_dest_id:
                move = self.env['stock.move'].create({
                    'name': "Outgoing move corresponding to proc %s" % proc.display_name,
                    'product_id': proc.product_id.id,
                    'product_uom_qty': proc.product_qty,
                    'product_uom': proc.product_uom.id,
                    'location_id': self.location_a.id,
                    'location_dest_id': self.location_b.id,
                    'date': proc.date_planned,
                    'origin': 'to_remove'
                })
                move.action_confirm()
                self.assertEqual(move.state, 'confirmed')
        self.env.invalidate_all()

    def test_10_planning_improved_reschedule(self):
        """Check rescheduling of purchase procurements."""
        company = self.browse_ref('base.main_company')
        company.po_lead = 1
        proc_env = self.env["procurement.order"]
        proc = proc_env.create({
            'name': 'Test Stock Schedule',
            'date_planned': '2015-02-02 00:00:00',
            'product_id': self.test_product.id,
            'product_qty': 10,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_a.id
        })
        proc.run()
        proc.check()
        self.create_move_out_corresponding_to_procs()
        # Rule "A => B" has been applied
        buy_in_a_rule = self.browse_ref('purchase_working_days.procurement_rule_buy_in_a')
        self.assertEqual(proc.rule_id, buy_in_a_rule)
        # Purchase order line has been created
        self.assertTrue(proc.purchase_line_id)
        pol = proc.purchase_line_id
        pol.compute_coverage_state()
        self.assertTrue(pol.date_required)
        self.assertEqual(pol.date_required[0:10], '2015-01-30')
        self.assertEqual(pol.date_planned[0:10], '2015-01-30')
        self.env['purchase.order'].cron_compute_limit_order_date()
        self.assertTrue(pol.limit_order_date)
        self.assertEqual(pol.limit_order_date[:10], '2015-01-21')
        self.assertEqual(pol.order_id.limit_order_date, pol.limit_order_date)
        for move in pol.move_ids:
            self.assertEqual(move.date[0:10], '2015-01-30')
            self.assertEqual(move.date_expected[0:10], '2015-01-30')

        # Let's reschedule the procurement (draft, date in the past)
        proc.date_planned = '2015-02-13 18:00:00'
        self.create_move_out_corresponding_to_procs()
        proc.action_reschedule()
        pol.compute_coverage_state()
        self.assertTrue(pol.date_required)
        self.assertEqual(pol.date_required[0:10], '2015-02-12')
        self.assertEqual(pol.date_planned[0:10], '2015-02-12')
        self.env['purchase.order'].cron_compute_limit_order_date()
        self.assertTrue(pol.limit_order_date)
        self.assertEqual(pol.limit_order_date[:10], '2015-02-03')
        self.assertEqual(pol.order_id.limit_order_date, pol.limit_order_date)
        for move in pol.move_ids:
            self.assertEqual(move.date[0:10], '2015-02-12')
            self.assertEqual(move.date_expected[0:10], '2015-01-30')

        # Latest date
        proc.date_planned = "2016-05-02 18:00:00"
        self.create_move_out_corresponding_to_procs()
        proc.action_reschedule()
        pol.compute_coverage_state()
        self.assertTrue(pol.date_required)
        self.assertEqual(pol.date_required[0:10], '2016-04-29')
        self.assertEqual(pol.date_planned[0:10], '2016-04-29')
        self.env['purchase.order'].cron_compute_limit_order_date()
        self.assertTrue(pol.limit_order_date)
        self.assertEqual(pol.limit_order_date[:10], '2016-04-20')
        self.assertEqual(pol.order_id.limit_order_date, pol.limit_order_date)
        for move in pol.move_ids:
            self.assertEqual(move.date[0:10], '2016-02-12')
            self.assertEqual(move.date_expected[0:10], '2016-01-30')

        # Let's reschedule the procurement (sent, date in the past)
        pol.order_id.state = 'sent'
        proc.date_planned = "2015-02-13 18:00:00"
        self.create_move_out_corresponding_to_procs()
        proc.action_reschedule()
        pol.compute_coverage_state()
        self.assertTrue(pol.date_required)
        self.assertEqual(pol.date_required[0:10], '2015-02-12')
        self.assertEqual(pol.date_planned[0:10], '2016-04-29')
        self.env['purchase.order'].cron_compute_limit_order_date()
        self.assertTrue(pol.limit_order_date)
        self.assertEqual(pol.limit_order_date[:10], '2015-02-03')
        self.assertEqual(pol.order_id.limit_order_date, pol.limit_order_date)
        for move in pol.move_ids:
            self.assertEqual(move.date[0:10], '2015-02-12')
            self.assertEqual(move.date_expected[0:10], '2015-01-30')

    def test_20_purchase_orderline_required_date(self):
        """Check Purchase Order Line required date."""
        company = self.browse_ref('base.main_company')
        company.po_lead = 1
        proc_env = self.env["procurement.order"]
        proc = proc_env.create({
            'name': 'Test Stock Schedule',
            'date_planned': '2015-02-02 00:00:00',
            'product_id': self.test_product.id,
            'product_qty': 10,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_a.id
        })
        proc2 = proc_env.create({
            'name': 'Test Stock Schedule',
            'date_planned': '2015-02-04 00:00:00',
            'product_id': self.test_product.id,
            'product_qty': 20,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_a.id
        })
        proc.run()
        proc2.run()
        self.assertEqual(proc.state, 'running')
        self.assertEqual(proc2.state, 'running')
        # Rule "A => B" has been applied
        buy_in_a_rule = self.browse_ref('purchase_working_days.procurement_rule_buy_in_a')
        self.assertEqual(proc.rule_id, buy_in_a_rule)
        self.assertEqual(proc2.rule_id, buy_in_a_rule)
        # Purchase order line has been created
        self.assertTrue(proc.purchase_line_id)
        pol = proc.purchase_line_id
        self.assertEqual(proc2.purchase_line_id, pol)
        self.create_move_out_corresponding_to_procs()
        pol.compute_coverage_state()
        self.assertTrue(pol.date_required)
        self.assertEqual(pol.date_required[0:10], '2015-01-30')
        self.assertEqual(pol.date_planned[0:10], '2015-01-30')
        self.env['purchase.order'].cron_compute_limit_order_date()
        self.assertTrue(pol.limit_order_date)
        self.assertEqual(pol.limit_order_date[:10], '2015-01-21')
        self.assertEqual(pol.order_id.limit_order_date, pol.limit_order_date)

    def test_30_opmsg(self):
        """
        Testing calculation of opmsg_reduce_qty, to_delete and remaining_qty
        """
        company = self.browse_ref('base.main_company')
        company.po_lead = 1
        proc_env = self.env["procurement.order"]
        proc = proc_env.create({
            'name': 'Test Stock Schedule',
            'date_planned': '2015-02-02 00:00:00',
            'product_id': self.test_product.id,
            'product_qty': 10,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_a.id
        })
        proc2 = proc_env.create({
            'name': 'Test Stock Schedule',
            'date_planned': '2015-02-04 00:00:00',
            'product_id': self.test_product.id,
            'product_qty': 20,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_a.id
        })
        proc.run()
        proc2.run()
        self.assertEqual(proc.state, 'running')
        self.assertEqual(proc2.state, 'running')
        # Rule "A => B" has been applied
        buy_in_a_rule = self.browse_ref('purchase_working_days.procurement_rule_buy_in_a')
        self.assertEqual(proc.rule_id, buy_in_a_rule)
        self.assertEqual(proc2.rule_id, buy_in_a_rule)
        # Purchase order line has been created
        self.assertTrue(proc.purchase_line_id)
        pol = proc.purchase_line_id
        self.assertEqual(proc2.purchase_line_id, pol)
        self.assertEqual(pol.product_qty, 30)
        # Case of quantity over need (because of MOQ for instance)
        pol.product_qty = 40
        self.create_move_out_corresponding_to_procs()
        pol.compute_coverage_state()
        self.assertTrue(pol.date_required)
        self.assertEqual(pol.date_required[0:10], '2015-01-30')
        self.assertEqual(pol.date_planned[0:10], '2015-01-30')
        self.env['purchase.order'].cron_compute_limit_order_date()
        self.assertTrue(pol.limit_order_date)
        self.assertEqual(pol.limit_order_date[:10], '2015-01-21')
        self.assertEqual(pol.order_id.limit_order_date, pol.limit_order_date)
        pol.compute_coverage_state()
        self.assertEqual(pol.opmsg_reduce_qty, 30)
        if self.env.user.lang == 'fr_FR':
            self.assertEqual(pol.opmsg_text, u"REDUIRE LA QTE à 30.0 Unit(s)")
        else:
            self.assertEqual(pol.opmsg_text, u"REDUCE QTY to 30.0 Unit(s)")

        move_out1 = self.env['stock.move'].search([('origin', '=', 'to_remove'),
                                                   ('product_id', '=', self.test_product.id),
                                                   ('product_qty', '=', 10),
                                                   ('date', '=', '2015-02-02 00:00:00')])
        move_out2 = self.env['stock.move'].search([('origin', '=', 'to_remove'),
                                                   ('product_id', '=', self.test_product.id),
                                                   ('product_qty', '=', 20),
                                                   ('date', '=', '2015-02-04 00:00:00')])
        move_out1.ensure_one()
        move_out2.ensure_one()

        # Case of date OK
        pol.product_qty = 30
        pol.compute_coverage_state()
        self.env.invalidate_all()
        if self.env.user.lang == 'fr_FR':
            self.assertEqual(pol.opmsg_text, u"EN RETARD de 0 jour(s)")
        else:
            self.assertEqual(pol.opmsg_text, u"LATE by 0 day(s)")

        # Case of late line
        self.assertEqual(pol.date_required, '2015-01-30')
        pol.date_planned = '2015-02-15'
        self.env.invalidate_all()
        if self.env.user.lang == 'fr_FR':
            self.assertEqual(pol.opmsg_text, u"EN RETARD de 16 jour(s)")
        else:
            self.assertEqual(pol.opmsg_text, u"LATE by 16 day(s)")

        # Case of early line
        pol.date_planned = '2015-01-15'
        self.env.invalidate_all()
        if self.env.user.lang == 'fr_FR':
            self.assertEqual(pol.opmsg_text, u"EN AVANCE de 15 jour(s)")
        else:
            self.assertEqual(pol.opmsg_text, u"EARLY by 15 day(s)")

        # Case of line to reduce
        move_out1.action_cancel()
        pol.compute_coverage_state()
        self.assertFalse(pol.to_delete)
        self.assertEqual(pol.opmsg_reduce_qty, 20)
        if self.env.user.lang == 'fr_FR':
            self.assertEqual(pol.opmsg_text, u"REDUIRE LA QTE à 20.0 Unit(s)")
        else:
            self.assertEqual(pol.opmsg_text, u"REDUCE QTY to 20.0 Unit(s)")

        # Case of line to delete
        move_out2.action_cancel()
        pol.compute_coverage_state()
        self.assertTrue(pol.to_delete)
        self.assertEqual(pol.opmsg_reduce_qty, 0)
        if self.env.user.lang == 'fr_FR':
            self.assertEqual(pol.opmsg_text, u"ANNULER LA LIGNE")
        else:
            self.assertEqual(pol.opmsg_text, u"CANCEL LINE")
