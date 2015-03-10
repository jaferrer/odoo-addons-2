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

class TestStockPlanningImproved(common.TransactionCase):

    def setUp(self):
        super(TestStockPlanningImproved, self).setUp()
        self.test_product = self.browse_ref("stock_working_days.product_test_product")
        self.location_a = self.browse_ref("stock_working_days.stock_location_a")
        self.location_b = self.browse_ref("stock_working_days.stock_location_b")
        self.location_c = self.browse_ref("stock_planning_improved.stock_location_c")
        self.location_inv = self.browse_ref("stock.location_inventory")
        self.product_uom_unit_id = self.ref("product.product_uom_unit")

    def test_10_planning_improved_reschedule(self):
        """Check rescheduling of advanced procurement."""
        proc_env = self.env["procurement.order"]
        proc = proc_env.create({
            'name': 'Test Stock Schedule',
            'date_planned': '2015-02-02 00:00:00',
            'product_id': self.test_product.id,
            'product_qty': 10,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_c.id
        })
        proc.run()
        proc.check()
        # Rule "A => B" has been applied
        b_to_c_rule = self.browse_ref('stock_planning_improved.procurement_rule_b_to_c')
        self.assertEqual(proc.rule_id, b_to_c_rule)
        # Moves have been created
        self.assertGreater(len(proc.move_ids), 0)
        # Move date and date expected are correctly set for each move
        for move in proc.move_ids:
            self.assertEqual(move.date[0:10], '2015-01-28')
            self.assertEqual(move.date_expected[0:10], '2015-01-28')
        # Check the procurement created by the first move
        proc2 = proc_env.search([('move_dest_id','=',proc.move_ids[0].id)])
        self.assertEqual(proc2.date_planned[0:10], '2015-01-28')
        proc2.run()
        proc2.check()
        a_to_b_rule = self.browse_ref('stock_working_days.procurement_rule_a_to_b')
        self.assertEqual(proc2.rule_id, a_to_b_rule)
        self.assertGreater(len(proc2.move_ids), 0)
        for move in proc2.move_ids:
            self.assertEqual(move.date[0:10], '2015-01-21')
            self.assertEqual(move.date_expected[0:10], '2015-01-21')

        # Let's reschedule the procurement
        proc.date_planned = "2015-02-10 10:00:00"
        proc.action_reschedule()
        # Check that the due date is changed but not the planned date
        for move in proc.move_ids:
            self.assertEqual(move.date[0:10], '2015-02-05')
            self.assertEqual(move.date_expected[0:10], '2015-01-28')
        # Check that the procurement made from the move is automatically rescheduled
        self.assertEqual(proc2.date_planned[0:10], '2015-02-05')
        for move in proc2.move_ids:
            self.assertEqual(move.date[0:10], '2015-01-29')
            self.assertEqual(move.date_expected[0:10], '2015-01-21')

        # Testing propagation of date_expected (and not of date)
        before = proc2.move_ids[0].date_expected
        proc2.move_ids[0].date_expected = after = "2015-01-23 19:00:00"
        self.assertEqual(proc2.move_dest_id.date_expected[0:10], "2015-01-30")
        self.assertEqual(proc2.move_dest_id.date[0:10], "2015-02-05")

    def test_20_check_action_done(self):
        """Check the dates when the moves are done."""
        proc_env = self.env["procurement.order"]
        proc = proc_env.create({
            'name': 'Test Stock Schedule',
            'date_planned': '2015-02-02 00:00:00',
            'product_id': self.test_product.id,
            'product_qty': 10,
            'product_uom': self.product_uom_unit_id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.location_b.id
        })
        proc.run()
        proc.check()
        # Rule "A => B" has been applied
        a_to_b_rule = self.browse_ref('stock_working_days.procurement_rule_a_to_b')
        self.assertEqual(proc.rule_id, a_to_b_rule)
        # Moves have been created
        self.assertGreater(len(proc.move_ids), 0)
        # Move date and date expected are correctly set for each move
        for move in proc.move_ids:
            self.assertEqual(move.date[0:10], '2015-01-26')
            self.assertEqual(move.date_expected[0:10], '2015-01-26')

        # Bring the product in source location
        move2 = self.env["stock.move"].create({
            'name': "Supply source location for test",
            'product_id': self.test_product.id,
            'product_uom': self.product_uom_unit_id,
            'product_uom_qty': 15,
            'location_id': self.location_inv.id,
            'location_dest_id': self.location_a.id,
        })
        move2.action_confirm()
        move2.action_done()

        for move in proc.move_ids:
            move.action_assign()
            self.assertEqual(move.state, "assigned")
            move.action_done()
            self.assertEqual(move.state, "done")
            self.assertEqual(move.date[0:10], '2015-01-26')
            self.assertEqual(move.date_expected[0:10], datetime.today().strftime("%Y-%m-%d"))

        # Let's reschedule the procurement and check that nothing happens
        proc.date_planned = '2015-02-15 10:00:00'
        proc.action_reschedule()
        for move in proc.move_ids:
            self.assertEqual(move.date[0:10], '2015-01-26')
            self.assertEqual(move.date_expected[0:10], datetime.today().strftime("%Y-%m-%d"))


