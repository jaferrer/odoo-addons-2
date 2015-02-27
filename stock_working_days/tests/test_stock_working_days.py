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

class TestStockWorkingDays(common.TransactionCase):

    def setUp(self):
        super(TestStockWorkingDays, self).setUp()


    def test_10_default_calendar_schedule(self):
        """Test scheduling when no specific calendar is defined."""
        company = self.browse_ref('base.main_company')
        proc_env = self.env["procurement.order"]
        proc = proc_env.create({
            'name': 'Test Stock Schedule',
            'date_planned': '2015-02-02 00:00:00',
            'product_id': self.ref('stock_working_days.product_test_product'),
            'product_qty': 1,
            'product_uom': self.ref('product.product_uom_unit'),
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock_working_days.stock_location_b')
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

    def test_20_schedule_company_calendar(self):
        """Schedule test with fallback on defined company calendar."""
        company = self.browse_ref('base.main_company')
        company.calendar_id = self.browse_ref('stock_working_days.demo_calendar_1')
        proc_env = self.env["procurement.order"]
        proc = proc_env.create({
            'name': 'Test Stock Schedule',
            'date_planned': '2015-02-02 00:00:00',
            'product_id': self.ref('stock_working_days.product_test_product'),
            'product_qty': 1,
            'product_uom': self.ref('product.product_uom_unit'),
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock_working_days.stock_location_b')
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
            self.assertEqual(move.date[0:10], '2015-01-12')
            self.assertEqual(move.date_expected[0:10], '2015-01-12')

    def test_30_schedule_warehouse_calendar(self):
        """Schedule test with a defined warehouse resource and a defined supplier resource."""
        company = self.browse_ref('base.main_company')
        proc_env = self.env["procurement.order"]
        resource_env = self.env["resource.resource"]
        leave_env = self.env["resource.calendar.leaves"]
        warehouse_id = self.browse_ref('stock.warehouse0')
        resource_w = resource_env.create({
            'name': "Warehouse0 resource",
            'calendar_id': self.ref('stock_working_days.demo_calendar_1')
        })
        leave_w = leave_env.create({
            'name': "Warehouse0 leave",
            'resource_id': resource_w.id,
            'calendar_id': self.ref('stock_working_days.demo_calendar_1'),
            'date_from': "2015-01-10",
            'date_to': "2015-01-25",
        })
        warehouse_id.resource_id = resource_w.id
        proc = proc_env.create({
            'name': 'Test Stock Schedule',
            'date_planned': '2015-02-02 00:00:00',
            'product_id': self.ref('stock_working_days.product_test_product'),
            'product_qty': 1,
            'product_uom': self.ref('product.product_uom_unit'),
            'warehouse_id': warehouse_id.id,
            'location_id': self.ref('stock_working_days.stock_location_b')
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
            self.assertEqual(move.date[0:10], '2014-12-29')
            self.assertEqual(move.date_expected[0:10], '2014-12-29')
