# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import pytz

from odoo.tests import common
from odoo import fields


class TestMrpWorkingDays(common.TransactionCase):

    def setUp(self):
        super(TestMrpWorkingDays, self).setUp()
        self.product = self.browse_ref('mrp_workorder_planning.product_test_product_mo')
        self.warehouse = self.browse_ref('stock.warehouse0')
        self.stock = self.browse_ref('stock.stock_location_stock')
        self.env.user.company_id.calendar_id = self.browse_ref('mrp_workorder_planning.calendar_1')

    def utcize_date(self, date):
        """Return UTC date of given date (as strings)"""
        dt = fields.Datetime.from_string(date)
        tz_info = fields.Datetime.context_timestamp(self.env.user, dt).tzinfo
        dt_utc = dt.replace(tzinfo=tz_info).astimezone(pytz.UTC).replace(tzinfo=None)
        return fields.Datetime.to_string(dt_utc)

    def test_10_schedule_days(self):
        company = self.browse_ref('base.main_company')
        date = fields.Datetime.from_string('2017-11-27 14:00:00')
        self.assertEqual(fields.Date.to_string(company.schedule_working_days(0, date)), '2017-11-27')
        self.assertEqual(fields.Date.to_string(company.schedule_working_days(1, date)), '2017-12-04')
        self.assertEqual(fields.Date.to_string(company.schedule_working_days(2, date)), '2017-12-06')
        self.assertEqual(fields.Date.to_string(company.schedule_working_days(-1, date)), '2017-11-22')
        self.assertEqual(fields.Date.to_string(company.schedule_working_days(-2, date)), '2017-11-20')

    def test_15_schedule_hours(self):
        workcenter = self.browse_ref('mrp_workorder_planning.test_workcenter_a')
        date = '2017-11-27 14:00:00'

        def compare_dates_scheduled(date_start, nb_hours, date_expected):
            """date_start and date_expected are in client tz"""
            dt_start = fields.Datetime.from_string(date_start)
            tz_info = fields.Datetime.context_timestamp(workcenter, dt_start).tzinfo
            dt_start_utc = dt_start.replace(tzinfo=tz_info).astimezone(pytz.UTC).replace(tzinfo=None)
            dt_end = workcenter.schedule_working_hours(nb_hours, dt_start_utc)
            dt_end_loc = fields.Datetime.context_timestamp(workcenter, dt_end).replace(tzinfo=None)
            self.assertEqual(fields.Datetime.to_string(dt_end_loc), date_expected)

        compare_dates_scheduled(date, 0, '2017-11-27 14:00:00')
        compare_dates_scheduled(date, 1, '2017-11-27 15:00:00')
        compare_dates_scheduled(date, 3, '2017-11-27 17:00:00')
        compare_dates_scheduled(date, 3.5, '2017-11-27 17:30:00')
        compare_dates_scheduled(date, 4, '2017-12-04 08:00:00')
        compare_dates_scheduled(date, 5, '2017-12-04 09:00:00')
        compare_dates_scheduled(date, -1, '2017-11-27 13:00:00')
        compare_dates_scheduled(date, -5, '2017-11-27 09:00:00')
        compare_dates_scheduled(date, -5.5, '2017-11-27 08:30:00')
        compare_dates_scheduled(date, -6, '2017-11-22 18:00:00')
        compare_dates_scheduled(date, -7, '2017-11-22 17:00:00')

        workcenter = self.browse_ref('mrp_workorder_planning.test_workcenter_b')
        date = '2017-11-30 14:00:00'
        compare_dates_scheduled(date, 0, '2017-11-30 14:00:00')
        compare_dates_scheduled(date, 1, '2017-11-30 15:00:00')
        compare_dates_scheduled(date, 2, '2017-11-30 16:00:00')
        compare_dates_scheduled(date, 2.5, '2017-11-30 16:30:00')
        compare_dates_scheduled(date, 3, '2017-12-05 10:00:00')
        compare_dates_scheduled(date, 4, '2017-12-05 11:00:00')
        compare_dates_scheduled(date, -1, '2017-11-30 13:00:00')
        compare_dates_scheduled(date, -3, '2017-11-30 11:00:00')
        compare_dates_scheduled(date, -3.5, '2017-11-30 10:30:00')
        compare_dates_scheduled(date, -4, '2017-11-28 17:00:00')
        compare_dates_scheduled(date, -5, '2017-11-28 16:00:00')

        date = '2017-12-01 14:00:00'
        compare_dates_scheduled(date, 0, '2017-12-05 10:00:00')

    def test_20_default_calendar_schedule(self):
        """Test scheduling production orders."""
        company = self.browse_ref('base.main_company')
        proc_env = self.env["procurement.order"]
        # Create Production order
        proc_mo = proc_env.create({
            'name': 'Test MRP Schedule',
            'date_planned': '2017-12-01 14:00:00',
            'product_id': self.product.id,
            'product_qty': 1,
            'product_uom': self.ref('product.product_uom_unit'),
            'warehouse_id': self.warehouse.id,
            'location_id': self.stock.id,
        })
        # Force company mo lead to 1
        company.manufacturing_lead = 1
        proc_mo.run()
        proc_mo.check()
        # MO has been created
        self.assertTrue(proc_mo.production_id.id)
        # MO Planned date
        production_order = proc_mo.production_id
        self.assertEqual(production_order.date_planned_finished, '2017-12-01 14:00:00')
        self.assertEqual(production_order.date_planned_start[:10], '2017-11-06')

        # Create workorders
        production_order.button_plan()
        self.assertEqual(len(production_order.workorder_ids), 2)
        last_order, first_order = self.env['mrp.workorder'], self.env['mrp.workorder']
        for order in production_order.workorder_ids:
            if order.next_work_order_id:
                first_order = order
            else:
                last_order = order
        self.assertEqual(last_order.date_planned_finished, production_order.date_planned_finished)
        self.assertEqual(last_order.date_planned_finished, '2017-12-01 14:00:00')
        self.assertEqual(last_order.date_planned_start, self.utcize_date('2017-11-30 13:40:00'))
        self.assertEqual(first_order.date_planned_finished, self.utcize_date('2017-11-30 13:40:00'))
        self.assertEqual(first_order.date_planned_start, self.utcize_date('2017-11-27 16:20:00'))
