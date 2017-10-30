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

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tests import common

class TestPurchaseWorkingDays(common.TransactionCase):

    def setUp(self):
        super(TestPurchaseWorkingDays, self).setUp()

    def test_10_default_calendar_schedule(self):
        """Test PO scheduling when no specific calendar is defined."""
        company = self.browse_ref('base.main_company')
        proc_env = self.env["procurement.order"]
        proc = proc_env.create({
            'name': 'Test Purchase Schedule',
            'date_planned': '2015-02-02 00:00:00',
            'product_id': self.ref('stock_working_days.product_test_product'),
            'product_qty': 1,
            'product_uom': self.ref('product.product_uom_unit'),
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock_working_days.stock_location_a')
        })
        # Force company po_lead to 1, just in case
        company.po_lead = 1
        # Run the proc_in_a procurement
        proc.run()
        proc.check()
        # RFQ has been created
        self.assertTrue(proc.purchase_id.id)
        # RFQ expected date
        rfq = proc.purchase_id
        self.assertEquals(len(rfq.order_line), 1)
        order_line = rfq.order_line[0]
        self.assertEqual(order_line.date_planned[0:10], '2015-01-30')
        self.assertEqual(rfq.minimum_planned_date[0:10], '2015-01-30')
        # RFQ order date
        self.assertEqual(rfq.date_order[0:10],'2015-01-21')

    def test_20_schedule_company_calendar(self):
        """PO schedule test with fallback on defined company calendar."""
        company = self.browse_ref('base.main_company')
        company.calendar_id = self.browse_ref('stock_working_days.demo_calendar_1')
        proc_env = self.env["procurement.order"]
        proc = proc_env.create({
            'name': 'Test Purchase Schedule',
            'date_planned': '2015-02-02 00:00:00',
            'product_id': self.ref('stock_working_days.product_test_product'),
            'product_qty': 1,
            'product_uom': self.ref('product.product_uom_unit'),
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock_working_days.stock_location_a')
        })
        # Force company po_lead to 1, just in case
        company.po_lead = 1
        # Run the proc_in_a procurement
        proc.run()
        proc.check()
        # RFQ has been created
        self.assertTrue(proc.purchase_id.id)
        # RFQ expected date
        rfq = proc.purchase_id
        self.assertEquals(len(rfq.order_line), 1)
        order_line = rfq.order_line[0]
        self.assertEqual(order_line.date_planned[0:10], '2015-01-26')
        self.assertEqual(rfq.minimum_planned_date[0:10], '2015-01-26')
        # RFQ order date => Check we falled back on default calendar and not company calendar
        self.assertEqual(rfq.date_order[0:10],'2015-01-15')

    def test_30_schedule_warehouse_calendar(self):
        """Schedule test with a defined supplier resource."""
        company = self.browse_ref('base.main_company')
        proc_env = self.env["procurement.order"]
        resource_env = self.env["resource.resource"]
        leave_env = self.env["resource.calendar.leaves"]
        warehouse_id = self.browse_ref('stock.warehouse0')
        supplier_id = self.browse_ref('purchase_working_days.test_supplier')
        resource_s = resource_env.create({
            'name': "Supplier resource",
            'calendar_id': self.ref('stock_working_days.demo_calendar_1')
        })
        leave_s = leave_env.create({
            'name': "Supplier leave",
            'resource_id': resource_s.id,
            'calendar_id': self.ref('stock_working_days.demo_calendar_1'),
            'date_from': "2014-12-15 00:00:00",
            'date_to': "2015-01-10 23:00:00",
        })
        supplier_id.resource_id = resource_s.id
        proc = proc_env.create({
            'name': 'Test Purchase Schedule',
            'date_planned': '2015-02-02 00:00:00',
            'product_id': self.ref('stock_working_days.product_test_product'),
            'product_qty': 1,
            'product_uom': self.ref('product.product_uom_unit'),
            'warehouse_id': warehouse_id.id,
            'location_id': self.ref('stock_working_days.stock_location_a')
        })
        # Force company po_lead to 1, just in case
        company.po_lead = 1
        # Run the proc_in_a procurement
        proc.run()
        proc.check()
        # RFQ has been created
        self.assertTrue(proc.purchase_id.id)
        # RFQ expected date
        rfq = proc.purchase_id
        self.assertEquals(len(rfq.order_line), 1)
        order_line = rfq.order_line[0]
        self.assertEqual(order_line.date_planned[0:10], '2015-01-30')
        self.assertEqual(rfq.minimum_planned_date[0:10], '2015-01-30')
        # RFQ order date
        self.assertEqual(rfq.date_order[0:10],'2014-12-08')

    def test_40_pol_date_planned(self):
        """Check correct date_planned in manual purchase_order_line creation."""
        # Note: Forward calculation starts from this morning 00:00, so it counts the first day
        # No calendar
        supplier_info = self.browse_ref("purchase_working_days.product_supplier_info_test")
        date1 = self.env['purchase.order.line']._get_date_planned(supplier_info, "2015-01-21 22:00:00")
        self.assertEqual(date1.strftime(DEFAULT_SERVER_DATETIME_FORMAT)[0:10], "2015-01-30")
        # With default company calendar
        company = self.browse_ref('base.main_company')
        company.calendar_id = self.browse_ref('stock_working_days.demo_calendar_1')
        date2 = self.env['purchase.order.line']._get_date_planned(supplier_info, "2015-01-15 22:00:00")
        self.assertEqual(date2.strftime(DEFAULT_SERVER_DATETIME_FORMAT)[0:10], "2015-01-26")
        # With supplier calendar
        resource_env = self.env["resource.resource"]
        leave_env = self.env["resource.calendar.leaves"]
        supplier_id = self.browse_ref('purchase_working_days.test_supplier')
        resource_s = resource_env.create({
            'name': "Supplier resource",
            'calendar_id': self.ref('stock_working_days.demo_calendar_1')
        })
        leave_s = leave_env.create({
            'name': "Supplier leave",
            'resource_id': resource_s.id,
            'calendar_id': self.ref('stock_working_days.demo_calendar_1'),
            'date_from': "2014-12-15",
            'date_to': "2015-01-10",
        })
        supplier_id.resource_id = resource_s.id
        date3 = self.env['purchase.order.line']._get_date_planned(supplier_info, "2014-12-08 12:00:00")
        self.assertEqual(date3.strftime(DEFAULT_SERVER_DATETIME_FORMAT)[0:10], "2015-02-02")

