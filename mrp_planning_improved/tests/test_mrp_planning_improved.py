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

from openerp.tests import common


class TestMrpPlanningImproved(common.TransactionCase):

    def setUp(self):
        super(TestMrpPlanningImproved, self).setUp()
        self.product_to_manufacture = self.browse_ref('mrp_planning_improved.product_to_manufacture1')
        self.rule_manufacture = self.browse_ref('mrp_planning_improved.rule_manufacture')

    def create_procurement_order_1(self):
        procurement = self.env['procurement.order'].create({
            'name': 'Procurement order 1 (MRP planning improved)',
            'product_id': self.product_to_manufacture.id,
            'product_qty': 2,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock.stock_location_stock'),
            'date_planned': '2015-05-04 15:00:00',
            'product_uom': self.ref('product.product_uom_unit'),
            'company_id': self.ref('base.main_company'),
            'rule_id': self.rule_manufacture.id,
        })
        procurement.company_id.manufacturing_lead = 1.0
        return procurement

    def test_10_mrp_planning_improved(self):

        """
        Testing rescheduling a procurement order with a manufacturing rule
        """

        procurement_order_1 = self.create_procurement_order_1()
        procurement_order_1.run()
        self.assertEqual(procurement_order_1.company_id.manufacturing_lead, 1.0)
        self.assertEqual(self.product_to_manufacture.produce_delay, 2.0)
        self.assertEqual(procurement_order_1.rule_id.action, 'manufacture')
        self.assertTrue(procurement_order_1.production_id)
        order = procurement_order_1.production_id
        self.assertFalse(order.taken_into_account)
        self.assertEqual(order.date_planned[:10], "2015-04-29")
        self.assertEqual(order.date_required[:10], "2015-04-29")
        self.assertEqual(order.procurement_id, procurement_order_1)
        self.assertTrue(procurement_order_1.production_id.move_created_ids)
        self.assertEqual(len(procurement_order_1.production_id.move_created_ids), 1)
        move_created = procurement_order_1.production_id.move_created_ids[0]
        self.assertEqual(move_created.date[:10], "2015-05-01")

        # First, without context, and order not taken into account
        procurement_order_1.date_planned = '2015-05-05 15:00:00'
        procurement_order_1.action_reschedule()
        self.assertEqual(order.date_required[:10], '2015-04-30')
        self.assertEqual(order.date_planned[:10], '2015-04-29')
        self.assertEqual(move_created.date[:10], '2015-05-01')
        self.assertEqual(move_created.date_expected[:10], "2015-04-30")

        # Next, with context, and order not taken into account
        procurement_order_1.date_planned = '2015-05-06 15:00:00'
        procurement_order_1.with_context({'reschedule_planned_date': True}).action_reschedule()
        self.assertEqual(order.date_required[:10], '2015-05-01')
        self.assertEqual(order.date_planned[:10], '2015-05-01')
        self.assertEqual(move_created.date[:10], '2015-05-04')
        self.assertEqual(move_created.date_expected[:10], '2015-05-01')

        # Next, without context, and order taken into account
        procurement_order_1.taken_into_account = True
        procurement_order_1.date_planned = '2015-05-07 15:00:00'
        procurement_order_1.action_reschedule()
        self.assertEqual(order.date_required[:10], '2015-05-04')
        self.assertEqual(order.date_planned[:10], '2015-05-01')
        self.assertEqual(move_created.date[:10], '2015-05-05')
        self.assertEqual(move_created.date_expected[:10], '2015-05-01')

        # Next, with context, and order taken into account
        procurement_order_1.date_planned = '2015-05-08 15:00:00'
        procurement_order_1.action_reschedule()
        self.assertEqual(order.date_required[:10], '2015-05-05')
        self.assertEqual(order.date_planned[:10], '2015-05-01')
        self.assertEqual(move_created.date[:10], '2015-05-06')
        self.assertEqual(move_created.date_expected[:10], '2015-05-01')

    def test_20_mrp_planning_improved(self):

        """
        Testing function write and rescheduling a manufacturing order
        """

        procurement_order_1 = self.create_procurement_order_1()
        procurement_order_1.run()
        self.assertEqual(procurement_order_1.company_id.manufacturing_lead, 1.0)
        self.assertEqual(procurement_order_1.rule_id.action, 'manufacture')
        self.assertTrue(procurement_order_1.production_id)
        order = procurement_order_1.production_id
        self.assertFalse(order.taken_into_account)
        self.assertEqual(order.date_planned[:10], '2015-04-29')
        order.date_required = order.date_planned
        self.assertTrue(procurement_order_1.production_id.move_created_ids)
        self.assertEqual(len(procurement_order_1.production_id.move_created_ids), 1)
        move_created = procurement_order_1.production_id.move_created_ids[0]
        initial_date_output = move_created.date

        self.assertEqual(len(order.move_lines), 2)
        [m1, m2] = [False] * 2
        for move in order.move_lines:
            if move.product_qty == 10.0:
                m1 = move
            if move.product_qty == 20.0:
                m2 = move
        self.assertTrue(m1 and m2)
        self.assertEqual(m1.date[:10], '2015-04-29')
        self.assertEqual(m2.date[:10], '2015-04-29')
        initial_date_expected_input = m1.date_expected
        self.assertEqual(m2.date_expected, initial_date_expected_input)

        # First, testing function write of purchase order
        order.date_planned = '2015-04-30 15:00:00'
        self.assertEqual(m1.date_expected, initial_date_expected_input)
        self.assertEqual(m2.date_expected, initial_date_expected_input)
        self.assertEqual(m1.date[:10], '2015-04-29')
        self.assertEqual(m2.date[:10], '2015-04-29')
        self.assertEqual(order.date_required[:10], '2015-04-29')
        self.assertEqual(move_created.date, initial_date_output)
        self.assertEqual(move_created.date_expected[:10], '2015-04-30')

        # Testing rescheduling: first, without context, and order not taken into account
        order.date_required = '2015-05-01 15:00:00'
        order.date_planned = '2015-04-30 15:00:00'
        self.assertFalse(order.taken_into_account)
        order.action_reschedule()
        self.assertEqual(m1.date_expected, initial_date_expected_input)
        self.assertEqual(m2.date_expected, initial_date_expected_input)
        self.assertEqual(m1.date[:10], '2015-05-01')
        self.assertEqual(m2.date[:10], '2015-05-01')
        self.assertEqual(move_created.date, initial_date_output)
        self.assertEqual(move_created.date_expected[:10], '2015-04-30')

        # Next, with context, and order not taken into account
        order.date_required = '2015-05-02 15:00:00'
        order.date_planned = '2015-05-01 15:00:00'
        self.assertFalse(order.taken_into_account)
        order.with_context({'reschedule_planned_date': True}).action_reschedule()
        self.assertEqual(m1.date_expected[:10], '2015-05-02')
        self.assertEqual(m2.date_expected[:10], '2015-05-02')
        self.assertEqual(m1.date[:10], '2015-05-02')
        self.assertEqual(m2.date[:10], '2015-05-02')
        self.assertEqual(move_created.date, initial_date_output)
        self.assertEqual(move_created.date_expected[:10], '2015-05-01')

        # Next, without context, and order taken into account
        order.date_required = '2015-05-03 15:00:00'
        order.date_planned = '2015-05-02 15:00:00'
        order.taken_into_account = True
        order.action_reschedule()
        self.assertEqual(m1.date_expected[:10], '2015-05-02')
        self.assertEqual(m2.date_expected[:10], '2015-05-02')
        self.assertEqual(m1.date[:10], '2015-05-02')
        self.assertEqual(m2.date[:10], '2015-05-02')
        self.assertEqual(move_created.date, initial_date_output)
        self.assertEqual(move_created.date_expected[:10], '2015-05-02')

        # Next, with context, and order taken into account
        order.date_required = '2015-05-04 15:00:00'
        order.date_planned = '2015-05-03 15:00:00'
        order.with_context({'reschedule_planned_date': True}).action_reschedule()
        self.assertEqual(m1.date_expected[:10], '2015-05-04')
        self.assertEqual(m2.date_expected[:10], '2015-05-04')
        self.assertEqual(m1.date[:10], '2015-05-03')
        self.assertEqual(m2.date[:10], '2015-05-03')
        self.assertEqual(move_created.date, initial_date_output)
        self.assertEqual(move_created.date_expected[:10], '2015-05-03')
