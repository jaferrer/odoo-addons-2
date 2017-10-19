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
        self.location_c = self.browse_ref("stock_planning_improved.stock_location_c")
        self.location_inv = self.browse_ref("stock.location_inventory")
        self.product_uom_unit_id = self.ref("product.product_uom_unit")

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
        # Rule "A => B" has been applied
        buy_in_a_rule = self.browse_ref('purchase_working_days.procurement_rule_buy_in_a')
        self.assertEqual(proc.rule_id, buy_in_a_rule)
        # Purchase order line has been created
        self.assertTrue(proc.purchase_line_id)
        pol_id = proc.purchase_line_id
        self.assertEqual(pol_id.date_required[0:10], '2015-01-30')
        self.assertEqual(pol_id.date_planned[0:10], '2015-01-30')
        for move in pol_id.move_ids:
            self.assertEqual(move.date[0:10], '2015-01-30')
            self.assertEqual(move.date_expected[0:10], '2015-01-30')

        # Let's reschedule the procurement (draft, date in the past)
        proc.date_planned = "2015-02-13 18:00:00"
        proc.action_reschedule()
        self.assertEqual(pol_id.date_required[0:10], '2015-02-12')
        self.assertEqual(pol_id.date_planned[0:10], '2015-02-12')
        for move in pol_id.move_ids:
            self.assertEqual(move.date[0:10], '2015-02-12')
            self.assertEqual(move.date_expected[0:10], '2015-01-30')

        # Latest date
        proc.date_planned = "2016-05-02 18:00:00"
        proc.action_reschedule()
        self.assertEqual(pol_id.date_required[0:10], '2016-04-29')
        self.assertEqual(pol_id.date_planned[0:10], '2016-04-29')
        for move in pol_id.move_ids:
            self.assertEqual(move.date[0:10], '2015-02-12')
            self.assertEqual(move.date_expected[0:10], '2015-01-30')

        # Let's reschedule the procurement (sent, date in the past)
        pol_id.order_id.state = 'sent'
        proc.date_planned = "2015-02-13 18:00:00"
        proc.action_reschedule()
        self.assertEqual(pol_id.date_required[0:10], '2015-02-12')
        self.assertEqual(pol_id.date_planned[0:10], '2016-04-29')
        for move in pol_id.move_ids:
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
            'product_qty': 10,
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
        pol_id = proc.purchase_line_id
        self.assertEqual(proc2.purchase_line_id, pol_id)
        self.assertEqual(pol_id.date_required[0:10], '2015-01-30')
        self.assertEqual(pol_id.date_planned[0:10], '2015-01-30')
