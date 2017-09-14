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


class TestTemplateTasksPlanningImproved(common.TransactionCase):
    def setUp(self):
        super(TestTemplateTasksPlanningImproved, self).setUp()
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

    def test_10_critical_task(self):
        """Testing the calculation of field 'critical_task'."""

        self.test_project.start_auto_planning()
        self.assertTrue(self.project_task_1.critical_task)
        self.assertTrue(self.project_task_2.critical_task)
        self.assertFalse(self.project_task_3.critical_task)
        self.assertTrue(self.project_task_4.critical_task)
        self.assertFalse(self.project_task_5.critical_task)
        self.assertFalse(self.project_task_6.critical_task)
        self.assertFalse(self.project_task_7.critical_task)
        self.assertTrue(self.project_task_8.critical_task)
        self.assertTrue(self.project_task_9.critical_task)
        self.assertFalse(self.project_task_10.critical_task)
        self.assertTrue(self.project_task_11.critical_task)

    def test_20_allocated_duration(self):
        """Testing calculation of fields 'allocated_duration_unit_tasks' and 'total_allocated_duration'."""
        self.assertEqual(self.project_task_1.allocated_duration_unit_tasks, 0)
        self.assertEqual(self.project_task_1.total_allocated_duration, 1)
        self.assertEqual(self.project_task_2.allocated_duration_unit_tasks, 0)
        self.assertEqual(self.project_task_2.total_allocated_duration, 3)
        self.assertEqual(self.project_task_3.allocated_duration_unit_tasks, 0)
        self.assertEqual(self.project_task_3.total_allocated_duration, 2)
        self.assertEqual(self.project_task_4.allocated_duration_unit_tasks, 0)
        self.assertEqual(self.project_task_4.total_allocated_duration, 5)
        self.assertEqual(self.project_task_5.allocated_duration_unit_tasks, 0)
        self.assertEqual(self.project_task_5.total_allocated_duration, 7)
        self.assertEqual(self.project_task_6.allocated_duration_unit_tasks, 0)
        self.assertEqual(self.project_task_6.total_allocated_duration, 4)
        self.assertEqual(self.project_task_7.allocated_duration_unit_tasks, 0)
        self.assertEqual(self.project_task_7.total_allocated_duration, 1)
        self.assertEqual(self.project_task_8.allocated_duration_unit_tasks, 0)
        self.assertEqual(self.project_task_8.total_allocated_duration, 4)
        self.assertEqual(self.project_task_9.allocated_duration_unit_tasks, 0)
        self.assertEqual(self.project_task_9.total_allocated_duration, 13)
        self.assertEqual(self.project_task_10.allocated_duration_unit_tasks, 0)
        self.assertEqual(self.project_task_10.total_allocated_duration, 6)
        self.assertEqual(self.project_task_11.allocated_duration_unit_tasks, 0)
        self.assertEqual(self.project_task_11.total_allocated_duration, 7)

        self.assertEqual(self.parent_task_0.allocated_duration_unit_tasks, 1)
        self.assertEqual(self.parent_task_0.total_allocated_duration, 2)
        self.assertEqual(self.parent_task_1.allocated_duration_unit_tasks, 22)
        self.assertEqual(self.parent_task_1.total_allocated_duration, 26)
        self.assertEqual(self.parent_task_2.allocated_duration_unit_tasks, 17)
        self.assertEqual(self.parent_task_2.total_allocated_duration, 19)
        self.assertEqual(self.parent_task_3.allocated_duration_unit_tasks, 13)
        self.assertEqual(self.parent_task_3.total_allocated_duration, 16)

    def test_30_auto_planning(self):
        """Testing the automatic planification of tasks"""

        # Using task 3 as reference task
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

        # Using task 5 as reference task
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

        #  Using task 8 as reference task
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
        self.project_task_2.taken_into_account=True
        self.project_task_4.taken_into_account=True
        with self.assertRaises(UserError):
            self.parent_task_1.expected_start_date = '2017-09-23 08:00:00'
        with self.assertRaises(UserError):
            self.parent_task_1.expected_end_date = '2017-08-31 18:00:00'
