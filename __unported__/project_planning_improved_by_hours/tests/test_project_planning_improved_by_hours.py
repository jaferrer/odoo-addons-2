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

from openerp.tests import common
from openerp.exceptions import UserError


class TestPlanningImprovedByHours(common.TransactionCase):
    def setUp(self):
        super(TestPlanningImprovedByHours, self).setUp()
        self.company = self.browse_ref('base.main_company')
        self.half_day_unit = self.browse_ref('project_planning_improved_by_hours.product_uom_unit_half_days')
        self.day_unit = self.browse_ref('product.product_uom_day')
        self.company.project_time_mode_id = self.half_day_unit
        self.test_project = self.browse_ref('project_planning_improved.project_planning_improved_test_project')
        self.parent_task_0 = self.browse_ref('project_planning_improved.parent_task_0')
        self.parent_task_1 = self.browse_ref('project_planning_improved.parent_task_1')
        self.parent_task_2 = self.browse_ref('project_planning_improved.parent_task_2')
        self.parent_task_3 = self.browse_ref('project_planning_improved.parent_task_3')
        self.project_task_1 = self.browse_ref('project_planning_improved.project_task_1')
        self.project_task_2 = self.browse_ref('project_planning_improved.project_task_2')
        self.project_task_3 = self.browse_ref('project_planning_improved.project_task_3')
        self.project_task_4 = self.browse_ref('project_planning_improved.project_task_4')
        self.project_task_5 = self.browse_ref('project_planning_improved.project_task_5')
        self.project_task_6 = self.browse_ref('project_planning_improved.project_task_6')
        self.project_task_7 = self.browse_ref('project_planning_improved.project_task_7')
        self.project_task_8 = self.browse_ref('project_planning_improved.project_task_8')
        self.project_task_9 = self.browse_ref('project_planning_improved.project_task_9')
        self.project_task_10 = self.browse_ref('project_planning_improved.project_task_10')
        self.project_task_11 = self.browse_ref('project_planning_improved.project_task_11')

    def test_10_auto_planning_by_days(self):
        """Testing the automatic planification of tasks by days : it still should work."""

        # Using task 3 as reference task
        self.company.project_time_mode_id = self.day_unit
        self.test_project.reference_task_id = self.project_task_3
        self.test_project.reference_task_end_date = '2017-09-07 18:00:00'
        self.test_project.start_auto_planning()
        self.assertEqual(self.project_task_3.objective_start_date[:10], '2017-09-05')
        self.assertEqual(self.project_task_3.objective_end_date[:10], '2017-09-07')
        self.assertEqual(self.project_task_2.objective_start_date[:10], '2017-09-05')
        self.assertEqual(self.project_task_2.objective_end_date[:10], '2017-09-08')
        self.assertEqual(self.project_task_1.objective_start_date[:10], '2017-09-04')
        self.assertEqual(self.project_task_1.objective_end_date[:10], '2017-09-05')
        self.assertEqual(self.project_task_4.objective_start_date[:10], '2017-09-08')
        self.assertEqual(self.project_task_4.objective_end_date[:10], '2017-09-15')
        self.assertEqual(self.project_task_5.objective_start_date[:10], '2017-09-06')
        self.assertEqual(self.project_task_5.objective_end_date[:10], '2017-09-15')
        self.assertEqual(self.project_task_6.objective_start_date[:10], '2017-09-05')
        self.assertEqual(self.project_task_6.objective_end_date[:10], '2017-09-11')
        self.assertEqual(self.project_task_7.objective_start_date[:10], '2017-09-11')
        self.assertEqual(self.project_task_7.objective_end_date[:10], '2017-09-12')
        self.assertEqual(self.project_task_8.objective_start_date[:10], '2017-09-15')
        self.assertEqual(self.project_task_8.objective_end_date[:10], '2017-09-21')
        self.assertEqual(self.project_task_9.objective_start_date[:10], '2017-09-04')
        self.assertEqual(self.project_task_9.objective_end_date[:10], '2017-09-21')
        self.assertEqual(self.project_task_10.objective_start_date[:10], '2017-09-21')
        self.assertEqual(self.project_task_10.objective_end_date[:10], '2017-09-29')
        self.assertEqual(self.project_task_11.objective_start_date[:10], '2017-09-21')
        self.assertEqual(self.project_task_11.objective_end_date[:10], '2017-10-02')
        for task in self.test_project.task_ids:
            self.assertEqual(task.objective_start_date, task.expected_start_date)
            self.assertEqual(task.objective_end_date, task.expected_end_date)
        # Rescheduling end date and transmit it to next tasks
        self.project_task_6.expected_end_date = '2017-09-12 18:00:00'
        self.assertEqual(self.project_task_7.expected_start_date, '2017-09-12 18:00:00')
        self.assertEqual(self.project_task_7.expected_end_date, '2017-09-13 18:00:00')
        self.assertTrue(self.project_task_6.taken_into_account)
        self.assertFalse(self.project_task_7.taken_into_account)
        self.project_task_6.taken_into_account = False
        # Forbidden to move task 7 out of parent task 1
        with self.assertRaises(UserError):
            self.project_task_6.expected_end_date = '2017-09-15 18:00:00'

        # Using task 5 as reference task
        self.test_project.task_ids.write({'taken_into_account': False})
        self.test_project.reference_task_id = self.project_task_5
        self.test_project.reference_task_end_date = '2017-09-07 18:00:00'
        self.test_project.start_auto_planning()
        self.assertEqual(self.project_task_5.objective_start_date[:10], '2017-08-29')
        self.assertEqual(self.project_task_5.objective_end_date[:10], '2017-09-07')
        self.assertEqual(self.project_task_8.objective_start_date[:10], '2017-09-07')
        self.assertEqual(self.project_task_8.objective_end_date[:10], '2017-09-13')
        self.assertEqual(self.project_task_9.objective_start_date[:10], '2017-08-25')
        self.assertEqual(self.project_task_9.objective_end_date[:10], '2017-09-13')
        self.assertEqual(self.project_task_10.objective_start_date[:10], '2017-09-13')
        self.assertEqual(self.project_task_10.objective_end_date[:10], '2017-09-21')
        self.assertEqual(self.project_task_11.objective_start_date[:10], '2017-09-13')
        self.assertEqual(self.project_task_11.objective_end_date[:10], '2017-09-22')
        self.assertEqual(self.project_task_4.objective_start_date[:10], '2017-08-31')
        self.assertEqual(self.project_task_4.objective_end_date[:10], '2017-09-07')
        self.assertEqual(self.project_task_2.objective_start_date[:10], '2017-08-28')
        self.assertEqual(self.project_task_2.objective_end_date[:10], '2017-08-31')
        self.assertEqual(self.project_task_6.objective_start_date[:10], '2017-08-31')
        self.assertEqual(self.project_task_6.objective_end_date[:10], '2017-09-06')
        self.assertEqual(self.project_task_7.objective_start_date[:10], '2017-09-06')
        self.assertEqual(self.project_task_7.objective_end_date[:10], '2017-09-07')
        self.assertEqual(self.project_task_3.objective_start_date[:10], '2017-08-28')
        self.assertEqual(self.project_task_3.objective_end_date[:10], '2017-08-30')
        self.assertEqual(self.project_task_1.objective_start_date[:10], '2017-08-25')
        self.assertEqual(self.project_task_1.objective_end_date[:10], '2017-08-28')
        for task in self.test_project.task_ids:
            self.assertEqual(task.objective_start_date, task.expected_start_date)
            self.assertEqual(task.objective_end_date, task.expected_end_date)
        # Rescheduling end date and transmit it to next tasks
        self.project_task_7.expected_start_date = '2017-09-05 18:00:00'
        self.assertEqual(self.project_task_6.expected_end_date, '2017-09-05 18:00:00')
        self.assertEqual(self.project_task_6.expected_start_date, '2017-08-31 08:00:00')
        self.assertTrue(self.project_task_7.taken_into_account)
        self.assertFalse(self.project_task_6.taken_into_account)
        self.project_task_7.taken_into_account = False
        # Forbidden to move task 6 out of parent task 1
        with self.assertRaises(UserError):
            self.project_task_7.expected_start_date = '2017-08-30 18:00:00'

        # Using task 8 as reference task
        self.test_project.task_ids.write({'taken_into_account': False})
        self.test_project.reference_task_id = self.project_task_8
        self.test_project.reference_task_end_date = '2017-09-07 18:00:00'
        self.test_project.start_auto_planning()
        self.assertEqual(self.project_task_8.objective_start_date[:10], '2017-09-01')
        self.assertEqual(self.project_task_8.objective_end_date[:10], '2017-09-07')
        self.assertEqual(self.project_task_9.objective_start_date[:10], '2017-08-21')
        self.assertEqual(self.project_task_9.objective_end_date[:10], '2017-09-07')
        self.assertEqual(self.project_task_10.objective_start_date[:10], '2017-09-07')
        self.assertEqual(self.project_task_10.objective_end_date[:10], '2017-09-15')
        self.assertEqual(self.project_task_11.objective_start_date[:10], '2017-09-07')
        self.assertEqual(self.project_task_11.objective_end_date[:10], '2017-09-18')
        self.assertEqual(self.project_task_4.objective_start_date[:10], '2017-08-25')
        self.assertEqual(self.project_task_4.objective_end_date[:10], '2017-09-01')
        self.assertEqual(self.project_task_5.objective_start_date[:10], '2017-08-23')
        self.assertEqual(self.project_task_5.objective_end_date[:10], '2017-09-01')
        self.assertEqual(self.project_task_6.objective_start_date[:10], '2017-08-25')
        self.assertEqual(self.project_task_6.objective_end_date[:10], '2017-08-31')
        self.assertEqual(self.project_task_7.objective_start_date[:10], '2017-08-31')
        self.assertEqual(self.project_task_7.objective_end_date[:10], '2017-09-01')
        self.assertEqual(self.project_task_3.objective_start_date[:10], '2017-08-22')
        self.assertEqual(self.project_task_3.objective_end_date[:10], '2017-08-24')
        self.assertEqual(self.project_task_2.objective_start_date[:10], '2017-08-22')
        self.assertEqual(self.project_task_2.objective_end_date[:10], '2017-08-25')
        self.assertEqual(self.project_task_1.objective_start_date[:10], '2017-08-21')
        self.assertEqual(self.project_task_1.objective_end_date[:10], '2017-08-22')
        for task in self.test_project.task_ids:
            self.assertEqual(task.objective_start_date, task.expected_start_date)
            self.assertEqual(task.objective_end_date, task.expected_end_date)

        # Checking TIA update
        self.parent_task_0.expected_start_date = '2017-08-15 18:00:00'
        self.assertTrue(self.parent_task_0.taken_into_account)
        self.parent_task_3.expected_end_date = '2017-09-25 18:00:00'
        self.assertTrue(self.parent_task_3.taken_into_account)

        # New auto_planning should not update these dates
        self.test_project.start_auto_planning()
        self.assertEqual(self.parent_task_0.expected_start_date, '2017-08-15 18:00:00')
        self.assertEqual(self.parent_task_3.expected_end_date, '2017-09-25 18:00:00')

        # Checking that expected_start_date is always before expected_end_date
        self.assertEqual(self.project_task_11.expected_end_date[:10], '2017-09-18')
        with self.assertRaises(UserError):
            self.project_task_11.expected_start_date = '2017-09-19 18:00:00'

        # Checking that children tasks must always be included in their parent tasks.
        with self.assertRaises(UserError):
            self.project_task_2.expected_start_date = '2017-08-21 18:00:00'
        with self.assertRaises(UserError):
            self.project_task_11.expected_end_date = '2017-09-28 18:00:00'

        # Checking that parent tasks must always include their children tasks.
        self.project_task_2.taken_into_account = True
        self.project_task_4.taken_into_account = True
        with self.assertRaises(UserError):
            self.parent_task_1.expected_start_date = '2017-09-23 08:00:00'
        with self.assertRaises(UserError):
            self.parent_task_1.expected_end_date = '2017-08-31 18:00:00'

    def test_20_auto_planning_by_hours(self):
        """Testing the automatic planification of tasks by days : it still should work."""

        # Using task 3 as reference task
        self.company.project_time_mode_id = self.half_day_unit
        self.test_project.reference_task_id = self.project_task_3
        self.test_project.reference_task_end_date = '2017-09-07 18:00:00'
        self.test_project.start_auto_planning()
        self.assertEqual(self.project_task_3.objective_start_date, '2017-09-07 08:00:00')
        self.assertEqual(self.project_task_3.objective_end_date, '2017-09-07 18:00:00')
        self.assertEqual(self.project_task_2.objective_start_date, '2017-09-07 08:00:00')
        self.assertEqual(self.project_task_2.objective_end_date, '2017-09-08 13:30:00')
        self.assertEqual(self.project_task_1.objective_start_date, '2017-09-06 13:30:00')
        self.assertEqual(self.project_task_1.objective_end_date, '2017-09-07 08:00:00')
        self.assertEqual(self.project_task_6.objective_start_date, '2017-09-07 08:00:00')
        self.assertEqual(self.project_task_6.objective_end_date, '2017-09-08 18:00:00')
        self.assertEqual(self.project_task_7.objective_start_date, '2017-09-11 08:00:00')
        self.assertEqual(self.project_task_7.objective_end_date, '2017-09-11 13:30:00')
        self.assertEqual(self.project_task_4.objective_start_date, '2017-09-08 13:30:00')
        self.assertEqual(self.project_task_4.objective_end_date, '2017-09-12 18:00:00')
        self.assertEqual(self.project_task_5.objective_start_date, '2017-09-07 13:30:00')
        self.assertEqual(self.project_task_5.objective_end_date, '2017-09-13 08:00:00')
        self.assertEqual(self.project_task_8.objective_start_date, '2017-09-13 08:00:00')
        self.assertEqual(self.project_task_8.objective_end_date, '2017-09-14 18:00:00')
        self.assertEqual(self.project_task_9.objective_start_date, '2017-09-06 13:30:00')
        self.assertEqual(self.project_task_9.objective_end_date, '2017-09-15 08:00:00')
        self.assertEqual(self.project_task_10.objective_start_date, '2017-09-15 08:00:00')
        self.assertEqual(self.project_task_10.objective_end_date, '2017-09-19 18:00:00')
        self.assertEqual(self.project_task_11.objective_start_date, '2017-09-15 08:00:00')
        self.assertEqual(self.project_task_11.objective_end_date, '2017-09-20 13:30:00')
        for task in self.test_project.task_ids:
            self.assertEqual(task.objective_start_date, task.expected_start_date)
            self.assertEqual(task.objective_end_date, task.expected_end_date)

        # Using task 5 as reference task
        self.test_project.reference_task_id = self.project_task_5
        self.test_project.reference_task_end_date = '2017-09-07 18:00:00'
        self.test_project.start_auto_planning()
        self.assertEqual(self.project_task_5.objective_start_date, '2017-09-04 13:30:00')
        self.assertEqual(self.project_task_5.objective_end_date, '2017-09-07 18:00:00')
        self.assertEqual(self.project_task_8.objective_start_date, '2017-09-08 08:00:00')
        self.assertEqual(self.project_task_8.objective_end_date, '2017-09-11 18:00:00')
        self.assertEqual(self.project_task_9.objective_start_date, '2017-09-01 13:30:00')
        self.assertEqual(self.project_task_9.objective_end_date, '2017-09-12 08:00:00')
        self.assertEqual(self.project_task_10.objective_start_date, '2017-09-12 08:00:00')
        self.assertEqual(self.project_task_10.objective_end_date, '2017-09-14 18:00:00')
        self.assertEqual(self.project_task_11.objective_start_date, '2017-09-12 08:00:00')
        self.assertEqual(self.project_task_11.objective_end_date, '2017-09-15 13:30:00')
        self.assertEqual(self.project_task_7.objective_start_date, '2017-09-07 13:30:00')
        self.assertEqual(self.project_task_7.objective_end_date, '2017-09-08 08:00:00')
        self.assertEqual(self.project_task_6.objective_start_date, '2017-09-05 13:30:00')
        self.assertEqual(self.project_task_6.objective_end_date, '2017-09-07 13:30:00')
        self.assertEqual(self.project_task_4.objective_start_date, '2017-09-05 13:30:00')
        self.assertEqual(self.project_task_4.objective_end_date, '2017-09-08 08:00:00')
        self.assertEqual(self.project_task_2.objective_start_date, '2017-09-04 08:00:00')
        self.assertEqual(self.project_task_2.objective_end_date, '2017-09-05 13:30:00')
        self.assertEqual(self.project_task_3.objective_start_date, '2017-09-04 08:00:00')
        self.assertEqual(self.project_task_3.objective_end_date, '2017-09-04 18:00:00')
        self.assertEqual(self.project_task_1.objective_start_date, '2017-09-01 13:30:00')
        self.assertEqual(self.project_task_1.objective_end_date, '2017-09-04 08:00:00')
        for task in self.test_project.task_ids:
            self.assertEqual(task.objective_start_date, task.expected_start_date)
            self.assertEqual(task.objective_end_date, task.expected_end_date)

        #  Using task 8 as reference task
        self.test_project.reference_task_id = self.project_task_8
        self.test_project.reference_task_end_date = '2017-09-07 18:00:00'
        self.test_project.start_auto_planning()
        self.assertEqual(self.project_task_8.objective_start_date, '2017-09-06 08:00:00')
        self.assertEqual(self.project_task_8.objective_end_date, '2017-09-07 18:00:00')
        self.assertEqual(self.project_task_9.objective_start_date, '2017-08-30 13:30:00')
        self.assertEqual(self.project_task_9.objective_end_date, '2017-09-08 08:00:00')
        self.assertEqual(self.project_task_10.objective_start_date, '2017-09-08 08:00:00')
        self.assertEqual(self.project_task_10.objective_end_date, '2017-09-12 18:00:00')
        self.assertEqual(self.project_task_11.objective_start_date, '2017-09-08 08:00:00')
        self.assertEqual(self.project_task_11.objective_end_date, '2017-09-13 13:30:00')
        self.assertEqual(self.project_task_4.objective_start_date, '2017-09-01 13:30:00')
        self.assertEqual(self.project_task_4.objective_end_date, '2017-09-06 08:00:00')
        self.assertEqual(self.project_task_5.objective_start_date, '2017-08-31 13:30:00')
        self.assertEqual(self.project_task_5.objective_end_date, '2017-09-06 08:00:00')
        self.assertEqual(self.project_task_7.objective_start_date, '2017-09-05 13:30:00')
        self.assertEqual(self.project_task_7.objective_end_date, '2017-09-06 08:00:00')
        self.assertEqual(self.project_task_6.objective_start_date, '2017-09-01 13:30:00')
        self.assertEqual(self.project_task_6.objective_end_date, '2017-09-05 13:30:00')
        self.assertEqual(self.project_task_3.objective_start_date, '2017-08-31 08:00:00')
        self.assertEqual(self.project_task_3.objective_end_date, '2017-08-31 18:00:00')
        self.assertEqual(self.project_task_2.objective_start_date, '2017-08-31 08:00:00')
        self.assertEqual(self.project_task_2.objective_end_date, '2017-09-01 13:30:00')
        self.assertEqual(self.project_task_1.objective_start_date, '2017-08-30 13:30:00')
        self.assertEqual(self.project_task_1.objective_end_date, '2017-08-31 08:00:00')
        for task in self.test_project.task_ids:
            self.assertEqual(task.objective_start_date, task.expected_start_date)
            self.assertEqual(task.objective_end_date, task.expected_end_date)

    def test_30_auto_planning_by_hours_in_days(self):
        """Scheduling tasks by hours, using day as refernce unit, and not integer durations"""

        self.company.project_time_mode_id = self.day_unit
        self.test_project.reference_task_id = self.project_task_3
        self.test_project.reference_task_end_date = '2017-09-07 18:00:00'
        self.project_task_3.objective_duration = 0.5
        self.test_project.start_auto_planning()
        self.assertEqual(self.project_task_3.objective_start_date, '2017-09-07 13:30:00')
        self.assertEqual(self.project_task_3.objective_end_date, '2017-09-07 18:00:00')
        for task in self.test_project.task_ids:
            self.assertEqual(task.objective_start_date, task.expected_start_date)
            self.assertEqual(task.objective_end_date, task.expected_end_date)

        # Testing en date outside working hours
        self.test_project.reference_task_end_date = '2017-09-07 23:00:00'
        self.project_task_3.objective_duration = 0.5
        self.test_project.start_auto_planning()
        self.assertEqual(self.project_task_3.objective_start_date, '2017-09-07 13:30:00')
        self.assertEqual(self.project_task_3.objective_end_date, '2017-09-07 23:00:00')
        for task in self.test_project.task_ids:
            self.assertEqual(task.objective_start_date, task.expected_start_date)
            self.assertEqual(task.objective_end_date, task.expected_end_date)
