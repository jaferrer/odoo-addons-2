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
from ..models.exceptions import NotReschedulableTiaTaskError, StartDateNotWorkingPeriod, ReDisplayTaskForbidden


class TestTemplateTasksPlanningImproved(common.TransactionCase):
    def setUp(self):
        super(TestTemplateTasksPlanningImproved, self).setUp()
        self.test_project = self.browse_ref('project_planning_improved.project_planning_improved_test_project')
        self.demo_user = self.browse_ref('base.user_demo')
        self.parent_task_1 = self.browse_ref('project_planning_improved.parent_task_1')
        self.parent_task_2 = self.browse_ref('project_planning_improved.parent_task_2')
        self.parent_task_3 = self.browse_ref('project_planning_improved.parent_task_3')
        self.parent_task_4 = self.browse_ref('project_planning_improved.parent_task_4')
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

    def test_01_critical_task(self):
        """Testing the calculation of field 'critical_task'."""

        self.test_project.start_auto_planning()
        self.assertTrue(self.project_task_1.critical_task)
        self.assertTrue(self.project_task_2.critical_task)
        self.assertFalse(self.project_task_3.critical_task)
        self.assertTrue(self.project_task_4.critical_task)
        self.assertFalse(self.project_task_5.critical_task)
        self.assertFalse(self.project_task_6.critical_task)
        self.assertFalse(self.project_task_7.critical_task)
        self.assertFalse(self.project_task_8.critical_task)
        self.assertTrue(self.project_task_9.critical_task)
        self.assertFalse(self.project_task_10.critical_task)
        self.assertTrue(self.project_task_11.critical_task)
        self.assertFalse(self.parent_task_1.critical_task)
        self.assertFalse(self.parent_task_2.critical_task)
        self.assertFalse(self.parent_task_3.critical_task)
        self.assertFalse(self.parent_task_4.critical_task)

    def test_02_allocated_duration(self):
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
        self.assertEqual(self.project_task_9.total_allocated_duration, 5)
        self.assertEqual(self.project_task_10.allocated_duration_unit_tasks, 0)
        self.assertEqual(self.project_task_10.total_allocated_duration, 6)
        self.assertEqual(self.project_task_11.allocated_duration_unit_tasks, 0)
        self.assertEqual(self.project_task_11.total_allocated_duration, 7)

        self.assertEqual(self.parent_task_1.allocated_duration_unit_tasks, 1)
        self.assertEqual(self.parent_task_1.total_allocated_duration, 2)
        self.assertEqual(self.parent_task_2.allocated_duration_unit_tasks, 22)
        self.assertEqual(self.parent_task_2.total_allocated_duration, 26)
        self.assertEqual(self.parent_task_3.allocated_duration_unit_tasks, 9)
        self.assertEqual(self.parent_task_3.total_allocated_duration, 11)
        self.assertEqual(self.parent_task_4.allocated_duration_unit_tasks, 13)
        self.assertEqual(self.parent_task_4.total_allocated_duration, 16)

    def test_03_schedule_from_task_3(self):
        """First planification test, using task 3 as reference task"""

        self.test_project.reference_task_id = self.project_task_3
        self.test_project.reference_task_end_date = '2017-09-07'
        self.test_project.start_auto_planning()
        self.assertTrue(self.project_task_3.taken_into_account)
        self.assertEqual(self.project_task_3.objective_start_date, '2017-09-06')
        self.assertEqual(self.project_task_3.objective_end_date, '2017-09-07')
        self.assertEqual(self.project_task_1.objective_start_date, '2017-09-05')
        self.assertEqual(self.project_task_1.objective_end_date, '2017-09-05')
        self.assertEqual(self.project_task_2.objective_start_date, '2017-09-06')
        self.assertEqual(self.project_task_2.objective_end_date, '2017-09-08')
        self.assertEqual(self.project_task_4.objective_start_date, '2017-09-11')
        self.assertEqual(self.project_task_4.objective_end_date, '2017-09-15')
        self.assertEqual(self.project_task_5.objective_start_date, '2017-09-07')
        self.assertEqual(self.project_task_5.objective_end_date, '2017-09-15')
        self.assertEqual(self.project_task_6.objective_start_date, '2017-09-06')
        self.assertEqual(self.project_task_6.objective_end_date, '2017-09-11')
        self.assertEqual(self.project_task_7.objective_start_date, '2017-09-12')
        self.assertEqual(self.project_task_7.objective_end_date, '2017-09-12')
        self.assertEqual(self.project_task_8.objective_start_date, '2017-09-18')
        self.assertEqual(self.project_task_8.objective_end_date, '2017-09-21')
        self.assertEqual(self.project_task_9.objective_start_date, '2017-09-18')
        self.assertEqual(self.project_task_9.objective_end_date, '2017-10-04')
        self.assertEqual(self.project_task_10.objective_start_date, '2017-10-05')
        self.assertEqual(self.project_task_10.objective_end_date, '2017-10-12')
        self.assertEqual(self.project_task_11.objective_start_date, '2017-10-05')
        self.assertEqual(self.project_task_11.objective_end_date, '2017-10-13')
        self.assertEqual(self.parent_task_1.objective_start_date, '2017-09-05')
        self.assertEqual(self.parent_task_1.objective_end_date, '2017-09-05')
        self.assertEqual(self.parent_task_2.objective_start_date, '2017-09-06')
        self.assertEqual(self.parent_task_2.objective_end_date, '2017-09-15')
        self.assertEqual(self.parent_task_3.objective_start_date, '2017-09-18')
        self.assertEqual(self.parent_task_3.objective_end_date, '2017-10-04')
        self.assertEqual(self.parent_task_4.objective_start_date, '2017-10-05')
        self.assertEqual(self.parent_task_4.objective_end_date, '2017-10-13')
        for task in self.test_project.task_ids:
            self.assertEqual(task.objective_start_date, task.expected_start_date)
            self.assertEqual(task.objective_end_date, task.expected_end_date)

    def test_04_auto_planning_task_no_next_task(self):
        """Testing the automatic scheduling of tasks. The reference task here has no next task"""

        self.test_03_schedule_from_task_3()
        # Rescheduling end date and transmit it to next tasks
        self.project_task_6.expected_end_date_display = '2017-09-12 15:00:00'
        self.env.invalidate_all()
        self.assertEqual(self.project_task_3.objective_start_date, '2017-09-06')
        self.assertEqual(self.project_task_3.objective_end_date, '2017-09-07')
        self.assertEqual(self.project_task_1.objective_start_date, '2017-09-05')
        self.assertEqual(self.project_task_1.objective_end_date, '2017-09-05')
        self.assertEqual(self.project_task_2.objective_start_date, '2017-09-06')
        self.assertEqual(self.project_task_2.objective_end_date, '2017-09-08')
        self.assertEqual(self.project_task_4.objective_start_date, '2017-09-11')
        self.assertEqual(self.project_task_4.objective_end_date, '2017-09-15')
        self.assertEqual(self.project_task_5.objective_start_date, '2017-09-07')
        self.assertEqual(self.project_task_5.objective_end_date, '2017-09-15')
        self.assertEqual(self.project_task_6.objective_start_date, '2017-09-06')
        self.assertEqual(self.project_task_6.expected_end_date, '2017-09-12')
        self.assertEqual(self.project_task_7.expected_start_date, '2017-09-13')
        self.assertEqual(self.project_task_7.expected_end_date, '2017-09-13')
        self.assertEqual(self.project_task_8.objective_start_date, '2017-09-18')
        self.assertEqual(self.project_task_8.objective_end_date, '2017-09-21')
        self.assertEqual(self.project_task_9.objective_start_date, '2017-09-18')
        self.assertEqual(self.project_task_9.objective_end_date, '2017-10-04')
        self.assertEqual(self.project_task_10.objective_start_date, '2017-10-05')
        self.assertEqual(self.project_task_10.objective_end_date, '2017-10-12')
        self.assertEqual(self.project_task_11.objective_start_date, '2017-10-05')
        self.assertEqual(self.project_task_11.objective_end_date, '2017-10-13')
        self.assertEqual(self.parent_task_1.objective_start_date, '2017-09-05')
        self.assertEqual(self.parent_task_1.objective_end_date, '2017-09-05')
        self.assertEqual(self.parent_task_2.objective_start_date, '2017-09-06')
        self.assertEqual(self.parent_task_2.objective_end_date, '2017-09-15')
        self.assertEqual(self.parent_task_3.objective_start_date, '2017-09-18')
        self.assertEqual(self.parent_task_3.objective_end_date, '2017-10-04')
        self.assertEqual(self.parent_task_4.objective_start_date, '2017-10-05')
        self.assertEqual(self.parent_task_4.objective_end_date, '2017-10-13')
        self.assertFalse(self.project_task_1.taken_into_account)
        self.assertFalse(self.project_task_2.taken_into_account)
        self.assertTrue(self.project_task_3.taken_into_account)
        self.assertFalse(self.project_task_4.taken_into_account)
        self.assertFalse(self.project_task_5.taken_into_account)
        self.assertFalse(self.project_task_6.taken_into_account)
        self.assertFalse(self.project_task_7.taken_into_account)
        self.assertFalse(self.project_task_8.taken_into_account)
        self.assertFalse(self.project_task_9.taken_into_account)
        self.assertFalse(self.project_task_10.taken_into_account)
        self.assertFalse(self.project_task_11.taken_into_account)
        self.assertFalse(self.parent_task_1.taken_into_account)
        self.assertFalse(self.parent_task_2.taken_into_account)
        self.assertFalse(self.parent_task_3.taken_into_account)
        self.assertFalse(self.parent_task_4.taken_into_account)

    def test_05_reschedule_task_out_of_its_parent(self):

        self.test_03_schedule_from_task_3()

        self.project_task_6.expected_end_date = '2017-09-15'
        self.assertEqual(self.project_task_3.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_3.expected_end_date, '2017-09-07')
        self.assertEqual(self.project_task_1.expected_start_date, '2017-09-05')
        self.assertEqual(self.project_task_1.expected_end_date, '2017-09-05')
        self.assertEqual(self.project_task_2.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_2.expected_end_date, '2017-09-08')
        self.assertEqual(self.project_task_4.expected_start_date, '2017-09-11')
        self.assertEqual(self.project_task_4.expected_end_date, '2017-09-15')
        self.assertEqual(self.project_task_5.expected_start_date, '2017-09-07')
        self.assertEqual(self.project_task_5.expected_end_date, '2017-09-15')
        self.assertEqual(self.project_task_6.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_6.expected_end_date, '2017-09-15')
        self.assertEqual(self.project_task_7.expected_start_date, '2017-09-18')
        self.assertEqual(self.project_task_7.expected_end_date, '2017-09-18')
        self.assertEqual(self.project_task_8.expected_start_date, '2017-09-22')
        self.assertEqual(self.project_task_8.expected_end_date, '2017-09-27')
        self.assertEqual(self.project_task_9.expected_start_date, '2017-09-22')
        self.assertEqual(self.project_task_9.expected_end_date, '2017-10-10')
        self.assertEqual(self.project_task_10.expected_start_date, '2017-10-11')
        self.assertEqual(self.project_task_10.expected_end_date, '2017-10-18')
        self.assertEqual(self.project_task_11.expected_start_date, '2017-10-11')
        self.assertEqual(self.project_task_11.expected_end_date, '2017-10-19')
        self.assertEqual(self.parent_task_1.expected_start_date, '2017-09-05')
        self.assertEqual(self.parent_task_1.expected_end_date, '2017-09-05')
        self.assertEqual(self.parent_task_2.expected_start_date, '2017-09-06')
        self.assertEqual(self.parent_task_2.expected_end_date, '2017-09-18')
        self.assertEqual(self.parent_task_3.expected_start_date, '2017-09-22')
        self.assertEqual(self.parent_task_3.expected_end_date, '2017-10-10')
        self.assertEqual(self.parent_task_4.expected_start_date, '2017-10-11')
        self.assertEqual(self.parent_task_4.expected_end_date, '2017-10-19')

    def test_06_auto_planning_task_no_previous_task(self):
        """Testing the automatic scheduling of tasks. The reference task here has no previous task"""

        # Using task 5 as reference task
        self.test_project.task_ids.write({'taken_into_account': False})
        self.test_project.reference_task_id = self.project_task_5
        self.test_project.reference_task_end_date = '2017-09-07'
        self.test_project.start_auto_planning()
        self.assertEqual(self.project_task_5.objective_start_date, '2017-08-30')
        self.assertEqual(self.project_task_5.objective_end_date, '2017-09-07')
        self.assertEqual(self.project_task_8.objective_start_date, '2017-09-08')
        self.assertEqual(self.project_task_8.objective_end_date, '2017-09-13')
        self.assertEqual(self.project_task_9.objective_start_date, '2017-09-08')
        self.assertEqual(self.project_task_9.objective_end_date, '2017-09-26')
        self.assertEqual(self.project_task_10.objective_start_date, '2017-09-27')
        self.assertEqual(self.project_task_10.objective_end_date, '2017-10-04')
        self.assertEqual(self.project_task_11.objective_start_date, '2017-09-27')
        self.assertEqual(self.project_task_11.objective_end_date, '2017-10-05')
        self.assertEqual(self.project_task_4.objective_start_date, '2017-09-01')
        self.assertEqual(self.project_task_4.objective_end_date, '2017-09-07')
        self.assertEqual(self.project_task_2.objective_start_date, '2017-08-29')
        self.assertEqual(self.project_task_2.objective_end_date, '2017-08-31')
        self.assertEqual(self.project_task_7.objective_start_date, '2017-09-07')
        self.assertEqual(self.project_task_7.objective_end_date, '2017-09-07')
        self.assertEqual(self.project_task_6.objective_start_date, '2017-09-01')
        self.assertEqual(self.project_task_6.objective_end_date, '2017-09-06')
        self.assertEqual(self.project_task_3.objective_start_date, '2017-08-29')
        self.assertEqual(self.project_task_3.objective_end_date, '2017-08-30')
        self.assertEqual(self.project_task_1.objective_start_date, '2017-08-28')
        self.assertEqual(self.project_task_1.objective_end_date, '2017-08-28')
        self.assertEqual(self.parent_task_1.objective_start_date, '2017-08-28')
        self.assertEqual(self.parent_task_1.objective_end_date, '2017-08-28')
        self.assertEqual(self.parent_task_2.objective_start_date, '2017-08-29')
        self.assertEqual(self.parent_task_2.objective_end_date, '2017-09-07')
        self.assertEqual(self.parent_task_3.objective_start_date, '2017-09-08')
        self.assertEqual(self.parent_task_3.objective_end_date, '2017-09-26')
        self.assertEqual(self.parent_task_4.objective_start_date, '2017-09-27')
        self.assertEqual(self.parent_task_4.objective_end_date, '2017-10-05')
        for task in self.test_project.task_ids:
            self.assertEqual(task.objective_start_date, task.expected_start_date)
            self.assertEqual(task.objective_end_date, task.expected_end_date)

    def test_07_simple_reschedule_start_date(self):
        """Rescheduling start date and transmit it to previous tasks"""
        self.test_06_auto_planning_task_no_previous_task()
        self.project_task_7.expected_start_date = '2017-09-06'
        self.env.invalidate_all()
        self.assertEqual(self.project_task_5.expected_start_date, '2017-08-30')
        self.assertEqual(self.project_task_5.expected_end_date, '2017-09-07')
        self.assertEqual(self.project_task_8.expected_start_date, '2017-09-08')
        self.assertEqual(self.project_task_8.expected_end_date, '2017-09-13')
        self.assertEqual(self.project_task_9.expected_start_date, '2017-09-08')
        self.assertEqual(self.project_task_9.expected_end_date, '2017-09-26')
        self.assertEqual(self.project_task_10.expected_start_date, '2017-09-27')
        self.assertEqual(self.project_task_10.expected_end_date, '2017-10-04')
        self.assertEqual(self.project_task_11.expected_start_date, '2017-09-27')
        self.assertEqual(self.project_task_11.expected_end_date, '2017-10-05')
        self.assertEqual(self.project_task_4.expected_start_date, '2017-09-01')
        self.assertEqual(self.project_task_4.expected_end_date, '2017-09-07')
        self.assertEqual(self.project_task_2.expected_start_date, '2017-08-28')
        self.assertEqual(self.project_task_2.expected_end_date, '2017-08-30')
        self.assertEqual(self.project_task_7.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_7.expected_end_date, '2017-09-07')
        self.assertEqual(self.project_task_6.expected_end_date, '2017-09-05')
        self.assertEqual(self.project_task_6.expected_start_date, '2017-08-31')
        self.assertEqual(self.project_task_3.expected_start_date, '2017-08-28')
        self.assertEqual(self.project_task_3.expected_end_date, '2017-08-29')
        self.assertEqual(self.project_task_1.expected_start_date, '2017-08-25')
        self.assertEqual(self.project_task_1.expected_end_date, '2017-08-25')
        self.assertEqual(self.parent_task_1.expected_start_date, '2017-08-25')
        self.assertEqual(self.parent_task_1.expected_end_date, '2017-08-25')
        self.assertEqual(self.parent_task_2.expected_start_date, '2017-08-28')
        self.assertEqual(self.parent_task_2.expected_end_date, '2017-09-07')
        self.assertEqual(self.parent_task_3.expected_start_date, '2017-09-08')
        self.assertEqual(self.parent_task_3.expected_end_date, '2017-09-26')
        self.assertEqual(self.parent_task_4.expected_start_date, '2017-09-27')
        self.assertEqual(self.parent_task_4.expected_end_date, '2017-10-05')
        self.assertFalse(self.project_task_7.taken_into_account)
        self.project_task_7.taken_into_account = True
        self.assertFalse(self.project_task_6.taken_into_account)
        self.project_task_7.taken_into_account = False

    def test_08_reschedule_parent_task_with_propagation(self):
        """Testing the automatic rescheduling of previous tasks during manual moves of a parent task"""

        self.test_03_schedule_from_task_3()

        self.parent_task_2.expected_start_date = '2017-08-16'
        self.env.invalidate_all()
        self.assertEqual(self.project_task_3.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_3.expected_end_date, '2017-09-07')
        self.assertEqual(self.project_task_1.expected_start_date, '2017-08-15')
        self.assertEqual(self.project_task_1.expected_end_date, '2017-08-15')
        self.assertEqual(self.project_task_2.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_2.expected_end_date, '2017-09-08')
        self.assertEqual(self.project_task_4.expected_start_date, '2017-09-11')
        self.assertEqual(self.project_task_4.expected_end_date, '2017-09-15')
        self.assertEqual(self.project_task_5.expected_start_date, '2017-09-07')
        self.assertEqual(self.project_task_5.expected_end_date, '2017-09-15')
        self.assertEqual(self.project_task_6.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_6.expected_end_date, '2017-09-11')
        self.assertEqual(self.project_task_7.expected_start_date, '2017-09-12')
        self.assertEqual(self.project_task_7.expected_end_date, '2017-09-12')
        self.assertEqual(self.project_task_8.expected_start_date, '2017-09-18')
        self.assertEqual(self.project_task_8.expected_end_date, '2017-09-21')
        self.assertEqual(self.project_task_9.expected_start_date, '2017-09-18')
        self.assertEqual(self.project_task_9.expected_end_date, '2017-10-04')
        self.assertEqual(self.project_task_10.expected_start_date, '2017-10-05')
        self.assertEqual(self.project_task_10.expected_end_date, '2017-10-12')
        self.assertEqual(self.project_task_11.expected_start_date, '2017-10-05')
        self.assertEqual(self.project_task_11.expected_end_date, '2017-10-13')
        self.assertEqual(self.parent_task_1.expected_start_date, '2017-08-15')
        self.assertEqual(self.parent_task_1.expected_end_date, '2017-08-15')
        self.assertEqual(self.parent_task_2.expected_start_date, '2017-08-16')
        self.assertEqual(self.parent_task_2.expected_end_date, '2017-09-15')
        self.assertEqual(self.parent_task_3.expected_start_date, '2017-09-18')
        self.assertEqual(self.parent_task_3.expected_end_date, '2017-10-04')
        self.assertEqual(self.parent_task_4.expected_start_date, '2017-10-05')
        self.assertEqual(self.parent_task_4.expected_end_date, '2017-10-13')
        self.assertFalse(self.parent_task_1.taken_into_account)

    def test_09_reschedule_parent_and_raise_because_tia(self):

        self.test_03_schedule_from_task_3()
        self.parent_task_1.taken_into_account = True
        error = False
        try:
            self.parent_task_4.expected_end_date = '2017-07-11'
        except NotReschedulableTiaTaskError as e:
            error = e
        if error:
            self.assertEqual(e.task_id, self.parent_task_1)
        else:
            raise UserError(u"This test should raise an error")

    def test_10_reschedule_child_and_raise_because_tia_parent(self):
        """Testing the automatic rescheduling of next and previous tasks during manual moves of parent tasks"""

        self.test_03_schedule_from_task_3()
        self.parent_task_4.taken_into_account = True
        error = False
        try:
            self.project_task_11.expected_end_date = '2017-10-20'
        except NotReschedulableTiaTaskError as e:
            error = e
        if error:
            self.assertEqual(e.task_id, self.parent_task_4)
        else:
            raise UserError(u"This test should raise an error")

    def test_11_reschedule_children_tasks(self):
        """Testing the automatic rescheduling of children tasks during manual moves"""

        self.test_03_schedule_from_task_3()
        self.project_task_3.taken_into_account = False

        self.parent_task_3.expected_start_date = '2017-09-11'
        self.assertEqual(self.parent_task_3.expected_start_date, '2017-09-11')
        self.assertEqual(self.parent_task_3.expected_end_date, '2017-10-04')
        self.assertEqual(self.project_task_8.expected_start_date, '2017-09-18')
        self.assertEqual(self.project_task_8.expected_end_date, '2017-09-21')
        self.assertEqual(self.project_task_9.expected_start_date, '2017-09-18')
        self.assertEqual(self.project_task_9.expected_end_date, '2017-10-04')
        self.assertEqual(self.project_task_10.expected_start_date, '2017-10-05')
        self.assertEqual(self.project_task_10.expected_end_date, '2017-10-12')
        self.assertEqual(self.project_task_11.expected_start_date, '2017-10-05')
        self.assertEqual(self.project_task_11.expected_end_date, '2017-10-13')
        self.assertEqual(self.parent_task_4.expected_start_date, '2017-10-05')
        self.assertEqual(self.parent_task_4.expected_end_date, '2017-10-13')
        self.assertEqual(self.project_task_4.expected_start_date, '2017-09-04')
        self.assertEqual(self.project_task_4.expected_end_date, '2017-09-08')
        self.assertEqual(self.project_task_5.expected_start_date, '2017-08-31')
        self.assertEqual(self.project_task_5.expected_end_date, '2017-09-08')
        self.assertEqual(self.project_task_7.expected_start_date, '2017-09-05')
        self.assertEqual(self.project_task_7.expected_end_date, '2017-09-05')
        self.assertEqual(self.project_task_6.expected_start_date, '2017-08-30')
        self.assertEqual(self.project_task_6.expected_end_date, '2017-09-04')
        self.assertEqual(self.project_task_3.expected_start_date, '2017-08-30')
        self.assertEqual(self.project_task_3.expected_end_date, '2017-08-31')
        self.assertEqual(self.project_task_2.expected_start_date, '2017-08-30')
        self.assertEqual(self.project_task_2.expected_end_date, '2017-09-01')
        self.assertEqual(self.project_task_1.expected_start_date, '2017-08-29')
        self.assertEqual(self.project_task_1.expected_end_date, '2017-08-29')
        self.assertEqual(self.parent_task_1.expected_start_date, '2017-08-29')
        self.assertEqual(self.parent_task_1.expected_end_date, '2017-08-29')
        self.assertEqual(self.parent_task_2.expected_start_date, '2017-08-30')
        self.assertEqual(self.parent_task_2.expected_end_date, '2017-09-08')

    def test_12_reschedule_start_date_in_weekend(self):
        """Testing the manual scheduling of tasks out of working periods"""

        self.test_03_schedule_from_task_3()
        self.project_task_3.taken_into_account = False

        error = False
        try:
            self.project_task_3.expected_start_date = '2017-09-03'
        except StartDateNotWorkingPeriod as e:
            error = e
        if error:
            self.assertEqual(e.task_id, self.project_task_3)
            self.assertEqual(e.date, '2017-09-03')
        else:
            raise UserError(u"This test should raise an error")

    def test_13_slide_task_from_timeline(self):

        self.test_03_schedule_from_task_3()

        # Rescheduling both start and end dates for a parent task
        self.test_project.task_ids.write({'taken_into_account': False})
        self.assertEqual(self.parent_task_3.expected_start_date, '2017-09-18')
        self.assertEqual(self.parent_task_3.expected_end_date, '2017-10-04')
        context = self.env.context.copy()
        if not context.get('params'):
            context['params'] = {}
        context['params']['view_type'] = 'timeline'
        self.parent_task_3.with_context(context).write({
            'expected_start_date': '2017-09-27',
            'expected_end_date': '2017-10-13',
        })

        # Parent tasks 1 and 2 (and their children) should not have changed
        self.assertEqual(self.project_task_3.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_3.expected_end_date, '2017-09-07')
        self.assertEqual(self.project_task_1.expected_start_date, '2017-09-05')
        self.assertEqual(self.project_task_1.expected_end_date, '2017-09-05')
        self.assertEqual(self.project_task_2.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_2.expected_end_date, '2017-09-08')
        self.assertEqual(self.project_task_4.expected_start_date, '2017-09-11')
        self.assertEqual(self.project_task_4.expected_end_date, '2017-09-15')
        self.assertEqual(self.project_task_5.expected_start_date, '2017-09-07')
        self.assertEqual(self.project_task_5.expected_end_date, '2017-09-15')
        self.assertEqual(self.project_task_6.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_6.expected_end_date, '2017-09-11')
        self.assertEqual(self.project_task_7.expected_start_date, '2017-09-12')
        self.assertEqual(self.project_task_7.expected_end_date, '2017-09-12')
        self.assertEqual(self.parent_task_1.expected_start_date, '2017-09-05')
        self.assertEqual(self.parent_task_1.expected_end_date, '2017-09-05')
        self.assertEqual(self.parent_task_2.expected_start_date, '2017-09-06')
        self.assertEqual(self.parent_task_2.expected_end_date, '2017-09-15')

        # Tasks 8 to 11 should have been rescheduled, and their parents
        self.assertEqual(self.project_task_8.expected_start_date, '2017-09-27')
        self.assertEqual(self.project_task_8.expected_end_date, '2017-10-02')
        self.assertEqual(self.project_task_9.expected_start_date, '2017-09-27')
        self.assertEqual(self.project_task_9.expected_end_date, '2017-10-13')
        self.assertEqual(self.project_task_10.expected_start_date, '2017-10-16')
        self.assertEqual(self.project_task_10.expected_end_date, '2017-10-23')
        self.assertEqual(self.project_task_11.expected_start_date, '2017-10-16')
        self.assertEqual(self.project_task_11.expected_end_date, '2017-10-24')
        self.assertEqual(self.parent_task_3.expected_start_date, '2017-09-27')
        self.assertEqual(self.parent_task_3.expected_end_date, '2017-10-13')
        self.assertEqual(self.parent_task_4.expected_start_date, '2017-10-16')
        self.assertEqual(self.parent_task_4.expected_end_date, '2017-10-24')

        # Let's come back to first task position
        context = self.env.context.copy()
        if not context.get('params'):
            context['params'] = {}
        context['params']['view_type'] = 'timeline'
        self.parent_task_3.with_context(context).write({
            'expected_start_date': '2017-09-18',
            'expected_end_date': '2017-10-04',
        })

        # Parent tasks 1, 2 and 3 (and their children) should have been advanced of 7 days.
        self.assertEqual(self.project_task_3.expected_start_date, '2017-08-28')
        self.assertEqual(self.project_task_3.expected_end_date, '2017-08-29')
        self.assertEqual(self.project_task_1.expected_start_date, '2017-08-25')
        self.assertEqual(self.project_task_1.expected_end_date, '2017-08-25')
        self.assertEqual(self.project_task_2.expected_start_date, '2017-08-28')
        self.assertEqual(self.project_task_2.expected_end_date, '2017-08-30')
        self.assertEqual(self.project_task_4.expected_start_date, '2017-08-31')
        self.assertEqual(self.project_task_4.expected_end_date, '2017-09-06')
        self.assertEqual(self.project_task_5.expected_start_date, '2017-08-29')
        self.assertEqual(self.project_task_5.expected_end_date, '2017-09-06')

        self.assertEqual(self.project_task_6.expected_start_date, '2017-08-28')
        self.assertEqual(self.project_task_6.expected_end_date, '2017-08-31')
        self.assertEqual(self.project_task_7.expected_start_date, '2017-09-01')
        self.assertEqual(self.project_task_7.expected_end_date, '2017-09-01')

        self.assertEqual(self.project_task_8.expected_start_date, '2017-09-18')
        self.assertEqual(self.project_task_8.expected_end_date, '2017-09-21')
        self.assertEqual(self.project_task_9.expected_start_date, '2017-09-18')
        self.assertEqual(self.project_task_9.expected_end_date, '2017-10-04')
        self.assertEqual(self.project_task_10.expected_start_date, '2017-10-16')
        self.assertEqual(self.project_task_10.expected_end_date, '2017-10-23')
        self.assertEqual(self.project_task_11.expected_start_date, '2017-10-16')
        self.assertEqual(self.project_task_11.expected_end_date, '2017-10-24')
        self.assertEqual(self.parent_task_1.expected_start_date, '2017-08-25')
        self.assertEqual(self.parent_task_1.expected_end_date, '2017-08-25')
        self.assertEqual(self.parent_task_2.expected_start_date, '2017-08-28')
        self.assertEqual(self.parent_task_2.expected_end_date, '2017-09-06')
        self.assertEqual(self.parent_task_3.expected_start_date, '2017-09-18')
        self.assertEqual(self.parent_task_3.expected_end_date, '2017-10-04')
        self.assertEqual(self.parent_task_4.expected_start_date, '2017-10-16')
        self.assertEqual(self.parent_task_4.expected_end_date, '2017-10-24')

    def test_14_hide_macro_tasks_in_timeline_and_reschedule(self):
        """First planification test, using task 3 as reference task"""
        self.test_03_schedule_from_task_3()
        self.project_task_3.taken_into_account = False

        self.parent_task_2.set_task_on_one_day()
        self.assertTrue(self.parent_task_2.forced_duration_one_day)
        self.assertTrue(self.project_task_2.forced_duration_one_day)
        self.assertTrue(self.project_task_3.forced_duration_one_day)
        self.assertTrue(self.project_task_4.forced_duration_one_day)
        self.assertTrue(self.project_task_5.forced_duration_one_day)
        self.assertTrue(self.project_task_6.forced_duration_one_day)
        self.assertTrue(self.project_task_7.forced_duration_one_day)
        self.assertEqual(self.project_task_3.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_3.expected_end_date, '2017-09-06')
        self.assertEqual(self.project_task_1.expected_start_date, '2017-09-05')
        self.assertEqual(self.project_task_1.expected_end_date, '2017-09-05')
        self.assertEqual(self.project_task_2.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_2.expected_end_date, '2017-09-06')
        self.assertEqual(self.project_task_4.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_4.expected_end_date, '2017-09-06')
        self.assertEqual(self.project_task_5.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_5.expected_end_date, '2017-09-06')
        self.assertEqual(self.project_task_6.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_6.expected_end_date, '2017-09-06')
        self.assertEqual(self.project_task_7.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_7.expected_end_date, '2017-09-06')
        self.assertEqual(self.project_task_8.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_8.expected_end_date, '2017-09-11')
        self.assertEqual(self.project_task_9.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_9.expected_end_date, '2017-09-22')
        self.assertEqual(self.project_task_10.expected_start_date, '2017-09-25')
        self.assertEqual(self.project_task_10.expected_end_date, '2017-10-02')
        self.assertEqual(self.project_task_11.expected_start_date, '2017-09-25')
        self.assertEqual(self.project_task_11.expected_end_date, '2017-10-03')
        self.assertEqual(self.parent_task_1.expected_start_date, '2017-09-05')
        self.assertEqual(self.parent_task_1.expected_end_date, '2017-09-05')
        self.assertEqual(self.parent_task_2.expected_start_date, '2017-09-06')
        self.assertEqual(self.parent_task_2.expected_end_date, '2017-09-06')
        self.assertEqual(self.parent_task_3.expected_start_date, '2017-09-06')
        self.assertEqual(self.parent_task_3.expected_end_date, '2017-09-22')
        self.assertEqual(self.parent_task_4.expected_start_date, '2017-09-25')
        self.assertEqual(self.parent_task_4.expected_end_date, '2017-10-03')

        # Let's reschedule task 1 and reach parent task 2, to check that the planification can "cross" the hidden tasks
        self.project_task_1.expected_end_date = '2017-09-08'
        self.assertTrue(self.parent_task_2.forced_duration_one_day)
        self.assertTrue(self.project_task_2.forced_duration_one_day)
        self.assertTrue(self.project_task_3.forced_duration_one_day)
        self.assertTrue(self.project_task_4.forced_duration_one_day)
        self.assertTrue(self.project_task_5.forced_duration_one_day)
        self.assertTrue(self.project_task_6.forced_duration_one_day)
        self.assertTrue(self.project_task_7.forced_duration_one_day)
        self.assertEqual(self.project_task_3.expected_start_date, '2017-09-11')
        self.assertEqual(self.project_task_3.expected_end_date, '2017-09-11')
        self.assertEqual(self.project_task_1.expected_start_date, '2017-09-05')
        self.assertEqual(self.project_task_1.expected_end_date, '2017-09-08')
        self.assertEqual(self.project_task_2.expected_start_date, '2017-09-11')
        self.assertEqual(self.project_task_2.expected_end_date, '2017-09-11')
        self.assertEqual(self.project_task_4.expected_start_date, '2017-09-11')
        self.assertEqual(self.project_task_4.expected_end_date, '2017-09-11')
        self.assertEqual(self.project_task_5.expected_start_date, '2017-09-11')
        self.assertEqual(self.project_task_5.expected_end_date, '2017-09-11')
        self.assertEqual(self.project_task_6.expected_start_date, '2017-09-11')
        self.assertEqual(self.project_task_6.expected_end_date, '2017-09-11')
        self.assertEqual(self.project_task_7.expected_start_date, '2017-09-11')
        self.assertEqual(self.project_task_7.expected_end_date, '2017-09-11')
        self.assertEqual(self.project_task_8.expected_start_date, '2017-09-11')
        self.assertEqual(self.project_task_8.expected_end_date, '2017-09-14')
        self.assertEqual(self.project_task_9.expected_start_date, '2017-09-11')
        self.assertEqual(self.project_task_9.expected_end_date, '2017-09-27')
        self.assertEqual(self.project_task_10.expected_start_date, '2017-09-28')
        self.assertEqual(self.project_task_10.expected_end_date, '2017-10-05')
        self.assertEqual(self.project_task_11.expected_start_date, '2017-09-28')
        self.assertEqual(self.project_task_11.expected_end_date, '2017-10-06')
        self.assertEqual(self.parent_task_1.expected_start_date, '2017-09-05')
        self.assertEqual(self.parent_task_1.expected_end_date, '2017-09-08')
        self.assertEqual(self.parent_task_2.expected_start_date, '2017-09-11')
        self.assertEqual(self.parent_task_2.expected_end_date, '2017-09-11')
        self.assertEqual(self.parent_task_3.expected_start_date, '2017-09-11')
        self.assertEqual(self.parent_task_3.expected_end_date, '2017-09-27')
        self.assertEqual(self.parent_task_4.expected_start_date, '2017-09-28')
        self.assertEqual(self.parent_task_4.expected_end_date, '2017-10-06')

    def test_15_display_hidden_task_only_allowed_from_original_task(self):

        self.test_14_hide_macro_tasks_in_timeline_and_reschedule()
        error = False
        try:
            self.project_task_4.unset_task_on_one_day()
        except ReDisplayTaskForbidden as e:
            error = e
        if error:
            self.assertEqual(e.task_id, self.project_task_4)
        else:
            raise UserError(u"This test should raise an error")

    def test_16_display_hidden_task_only_allowed_from_original_task(self):

        self.test_14_hide_macro_tasks_in_timeline_and_reschedule()
        # Let's display parent task 2 and check the replanification
        self.assertEqual(self.project_task_2.nb_days_after_for_start, 0)
        self.assertEqual(self.project_task_2.nb_days_after_for_end, 2)
        self.assertEqual(self.project_task_3.nb_days_after_for_start, 0)
        self.assertEqual(self.project_task_3.nb_days_after_for_end, 1)
        self.assertEqual(self.project_task_4.nb_days_after_for_start, 3)
        self.assertEqual(self.project_task_4.nb_days_after_for_end, 7)
        self.assertEqual(self.project_task_5.nb_days_after_for_start, 1)
        self.assertEqual(self.project_task_5.nb_days_after_for_end, 7)
        self.assertEqual(self.project_task_6.nb_days_after_for_start, 0)
        self.assertEqual(self.project_task_6.nb_days_after_for_end, 3)
        self.assertEqual(self.project_task_7.nb_days_after_for_start, 4)
        self.assertEqual(self.project_task_7.nb_days_after_for_end, 4)

        # Let's display parent task 2
        self.parent_task_2.unset_task_on_one_day()

        self.assertFalse(self.parent_task_2.forced_duration_one_day)
        self.assertFalse(self.project_task_2.forced_duration_one_day)
        self.assertFalse(self.project_task_3.forced_duration_one_day)
        self.assertFalse(self.project_task_4.forced_duration_one_day)
        self.assertFalse(self.project_task_5.forced_duration_one_day)
        self.assertFalse(self.project_task_6.forced_duration_one_day)
        self.assertFalse(self.project_task_7.forced_duration_one_day)
        self.assertFalse(self.parent_task_2.hidden_from_task_id)
        self.assertFalse(self.project_task_2.hidden_from_task_id)
        self.assertFalse(self.project_task_3.hidden_from_task_id)
        self.assertFalse(self.project_task_4.hidden_from_task_id)
        self.assertFalse(self.project_task_5.hidden_from_task_id)
        self.assertFalse(self.project_task_6.hidden_from_task_id)
        self.assertFalse(self.project_task_7.hidden_from_task_id)
        self.assertFalse(self.parent_task_2.nb_days_after_for_start)
        self.assertFalse(self.project_task_2.nb_days_after_for_start)
        self.assertFalse(self.project_task_3.nb_days_after_for_start)
        self.assertFalse(self.project_task_4.nb_days_after_for_start)
        self.assertFalse(self.project_task_5.nb_days_after_for_start)
        self.assertFalse(self.project_task_6.nb_days_after_for_start)
        self.assertFalse(self.project_task_7.nb_days_after_for_start)
        self.assertFalse(self.parent_task_2.nb_days_after_for_end)
        self.assertFalse(self.project_task_2.nb_days_after_for_end)
        self.assertFalse(self.project_task_3.nb_days_after_for_end)
        self.assertFalse(self.project_task_4.nb_days_after_for_end)
        self.assertFalse(self.project_task_5.nb_days_after_for_end)
        self.assertFalse(self.project_task_6.nb_days_after_for_end)
        self.assertFalse(self.project_task_7.nb_days_after_for_end)

        self.assertEqual(self.project_task_3.expected_start_date, '2017-09-11')
        self.assertEqual(self.project_task_3.expected_end_date, '2017-09-12')
        self.assertEqual(self.project_task_1.expected_start_date, '2017-09-05')
        self.assertEqual(self.project_task_1.expected_end_date, '2017-09-08')
        self.assertEqual(self.project_task_2.expected_start_date, '2017-09-11')
        self.assertEqual(self.project_task_2.expected_end_date, '2017-09-13')
        self.assertEqual(self.project_task_4.expected_start_date, '2017-09-14')
        self.assertEqual(self.project_task_4.expected_end_date, '2017-09-20')
        self.assertEqual(self.project_task_5.expected_start_date, '2017-09-12')
        self.assertEqual(self.project_task_5.expected_end_date, '2017-09-20')
        self.assertEqual(self.project_task_6.expected_start_date, '2017-09-11')
        self.assertEqual(self.project_task_6.expected_end_date, '2017-09-14')
        self.assertEqual(self.project_task_7.expected_start_date, '2017-09-15')
        self.assertEqual(self.project_task_7.expected_end_date, '2017-09-15')
        self.assertEqual(self.project_task_8.expected_start_date, '2017-09-21')
        self.assertEqual(self.project_task_8.expected_end_date, '2017-09-26')
        self.assertEqual(self.project_task_9.expected_start_date, '2017-09-21')
        self.assertEqual(self.project_task_9.expected_end_date, '2017-10-09')
        self.assertEqual(self.project_task_10.expected_start_date, '2017-10-10')
        self.assertEqual(self.project_task_10.expected_end_date, '2017-10-17')
        self.assertEqual(self.project_task_11.expected_start_date, '2017-10-10')
        self.assertEqual(self.project_task_11.expected_end_date, '2017-10-18')
        self.assertEqual(self.parent_task_1.expected_start_date, '2017-09-05')
        self.assertEqual(self.parent_task_1.expected_end_date, '2017-09-08')
        self.assertEqual(self.parent_task_2.expected_start_date, '2017-09-11')
        self.assertEqual(self.parent_task_2.expected_end_date, '2017-09-20')
        self.assertEqual(self.parent_task_3.expected_start_date, '2017-09-21')
        self.assertEqual(self.parent_task_3.expected_end_date, '2017-10-09')
        self.assertEqual(self.parent_task_4.expected_start_date, '2017-10-10')
        self.assertEqual(self.parent_task_4.expected_end_date, '2017-10-18')

    def test_17_hide_tasks_in_timeline_and_reschedule(self):
        """First planification test, using task 3 as reference task"""
        self.test_03_schedule_from_task_3()
        self.project_task_3.taken_into_account = False

        # Let's hide task 6
        self.project_task_6.set_task_on_one_day()
        self.assertEqual(self.project_task_3.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_3.expected_end_date, '2017-09-07')
        self.assertEqual(self.project_task_1.expected_start_date, '2017-09-05')
        self.assertEqual(self.project_task_1.expected_end_date, '2017-09-05')
        self.assertEqual(self.project_task_2.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_2.expected_end_date, '2017-09-08')
        self.assertEqual(self.project_task_4.expected_start_date, '2017-09-11')
        self.assertEqual(self.project_task_4.expected_end_date, '2017-09-15')
        self.assertEqual(self.project_task_5.expected_start_date, '2017-09-07')
        self.assertEqual(self.project_task_5.expected_end_date, '2017-09-15')
        self.assertEqual(self.project_task_6.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_6.expected_end_date, '2017-09-06')
        self.assertEqual(self.project_task_7.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_7.expected_end_date, '2017-09-06')
        self.assertEqual(self.project_task_8.expected_start_date, '2017-09-18')
        self.assertEqual(self.project_task_8.expected_end_date, '2017-09-21')
        self.assertEqual(self.project_task_9.expected_start_date, '2017-09-18')
        self.assertEqual(self.project_task_9.expected_end_date, '2017-10-04')
        self.assertEqual(self.project_task_10.expected_start_date, '2017-10-05')
        self.assertEqual(self.project_task_10.expected_end_date, '2017-10-12')
        self.assertEqual(self.project_task_11.expected_start_date, '2017-10-05')
        self.assertEqual(self.project_task_11.expected_end_date, '2017-10-13')
        self.assertEqual(self.parent_task_1.expected_start_date, '2017-09-05')
        self.assertEqual(self.parent_task_1.expected_end_date, '2017-09-05')
        self.assertEqual(self.parent_task_2.expected_start_date, '2017-09-06')
        self.assertEqual(self.parent_task_2.expected_end_date, '2017-09-15')
        self.assertEqual(self.parent_task_3.expected_start_date, '2017-09-18')
        self.assertEqual(self.parent_task_3.expected_end_date, '2017-10-04')
        self.assertEqual(self.parent_task_4.expected_start_date, '2017-10-05')
        self.assertEqual(self.parent_task_4.expected_end_date, '2017-10-13')

        # Let's hide task 4
        self.project_task_4.set_task_on_one_day()
        self.assertEqual(self.project_task_3.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_3.expected_end_date, '2017-09-07')
        self.assertEqual(self.project_task_1.expected_start_date, '2017-09-05')
        self.assertEqual(self.project_task_1.expected_end_date, '2017-09-05')
        self.assertEqual(self.project_task_2.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_2.expected_end_date, '2017-09-08')
        self.assertEqual(self.project_task_4.expected_start_date, '2017-09-11')
        self.assertEqual(self.project_task_4.expected_end_date, '2017-09-11')
        self.assertEqual(self.project_task_5.expected_start_date, '2017-09-07')
        self.assertEqual(self.project_task_5.expected_end_date, '2017-09-15')
        self.assertEqual(self.project_task_6.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_6.expected_end_date, '2017-09-06')
        self.assertEqual(self.project_task_7.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_7.expected_end_date, '2017-09-06')
        self.assertEqual(self.project_task_8.expected_start_date, '2017-09-18')
        self.assertEqual(self.project_task_8.expected_end_date, '2017-09-21')
        self.assertEqual(self.project_task_9.expected_start_date, '2017-09-18')
        self.assertEqual(self.project_task_9.expected_end_date, '2017-10-04')
        self.assertEqual(self.project_task_10.expected_start_date, '2017-10-05')
        self.assertEqual(self.project_task_10.expected_end_date, '2017-10-12')
        self.assertEqual(self.project_task_11.expected_start_date, '2017-10-05')
        self.assertEqual(self.project_task_11.expected_end_date, '2017-10-13')
        self.assertEqual(self.parent_task_1.expected_start_date, '2017-09-05')
        self.assertEqual(self.parent_task_1.expected_end_date, '2017-09-05')
        self.assertEqual(self.parent_task_2.expected_start_date, '2017-09-06')
        self.assertEqual(self.parent_task_2.expected_end_date, '2017-09-15')
        self.assertEqual(self.parent_task_3.expected_start_date, '2017-09-18')
        self.assertEqual(self.parent_task_3.expected_end_date, '2017-10-04')
        self.assertEqual(self.parent_task_4.expected_start_date, '2017-10-05')
        self.assertEqual(self.parent_task_4.expected_end_date, '2017-10-13')

        # Let's hide task 5
        self.project_task_5.set_task_on_one_day()
        self.assertEqual(self.project_task_3.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_3.expected_end_date, '2017-09-07')
        self.assertEqual(self.project_task_1.expected_start_date, '2017-09-05')
        self.assertEqual(self.project_task_1.expected_end_date, '2017-09-05')
        self.assertEqual(self.project_task_2.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_2.expected_end_date, '2017-09-08')
        self.assertEqual(self.project_task_4.expected_start_date, '2017-09-11')
        self.assertEqual(self.project_task_4.expected_end_date, '2017-09-11')
        self.assertEqual(self.project_task_5.expected_start_date, '2017-09-07')
        self.assertEqual(self.project_task_5.expected_end_date, '2017-09-07')
        self.assertEqual(self.project_task_6.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_6.expected_end_date, '2017-09-06')
        self.assertEqual(self.project_task_7.expected_start_date, '2017-09-06')
        self.assertEqual(self.project_task_7.expected_end_date, '2017-09-06')
        self.assertEqual(self.project_task_8.expected_start_date, '2017-09-18')
        self.assertEqual(self.project_task_8.expected_end_date, '2017-09-21')
        self.assertEqual(self.project_task_9.expected_start_date, '2017-09-18')
        self.assertEqual(self.project_task_9.expected_end_date, '2017-10-04')
        self.assertEqual(self.project_task_10.expected_start_date, '2017-10-05')
        self.assertEqual(self.project_task_10.expected_end_date, '2017-10-12')
        self.assertEqual(self.project_task_11.expected_start_date, '2017-10-05')
        self.assertEqual(self.project_task_11.expected_end_date, '2017-10-13')
        self.assertEqual(self.parent_task_1.expected_start_date, '2017-09-05')
        self.assertEqual(self.parent_task_1.expected_end_date, '2017-09-05')
        self.assertEqual(self.parent_task_2.expected_start_date, '2017-09-06')
        self.assertEqual(self.parent_task_2.expected_end_date, '2017-09-11')
        self.assertEqual(self.parent_task_3.expected_start_date, '2017-09-18')
        self.assertEqual(self.parent_task_3.expected_end_date, '2017-10-04')
        self.assertEqual(self.parent_task_4.expected_start_date, '2017-10-05')
        self.assertEqual(self.parent_task_4.expected_end_date, '2017-10-13')

    def test_18_reference_task_modification_by_a_non_manager(self):
        self.test_project.reference_task_id = self.project_task_3
        self.test_project.reference_task_end_date = '2017-09-07'
        self.test_project.user_id = self.demo_user
        with self.assertRaises(UserError):
            self.test_project.sudo().write({'reference_task_end_date': '2017-09-08'})
