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


class TestTemplateTasksPlanningImproved(common.TransactionCase):
    def setUp(self):
        super(TestTemplateTasksPlanningImproved, self).setUp()
        self.stage0 = self.browse_ref('project.project_stage_0')
        self.stage1 = self.browse_ref('project.project_stage_1')
        self.stage2 = self.browse_ref('project.project_stage_data_1')
        self.stage3 = self.browse_ref('project.project_stage_data_2')
        self.template_task1 = self.browse_ref('project_template_tasks.project_task_1')
        self.template_task2 = self.browse_ref('project_template_tasks.project_task_2')
        self.template_task3 = self.browse_ref('project_template_tasks.project_task_3')
        self.template_task4 = self.browse_ref('project_template_tasks.project_task_4')
        self.template_task5 = self.browse_ref('project_template_tasks.project_task_5')
        self.template_task6 = self.browse_ref('project_template_tasks.project_task_6')
        self.template_task7 = self.browse_ref('project_template_tasks.project_task_7')
        self.template_task8 = self.browse_ref('project_template_tasks.project_task_8')
        self.template_task9 = self.browse_ref('project_template_tasks.project_task_9')
        self.template_task10 = self.browse_ref('project_template_tasks.project_task_10')
        self.template_task11 = self.browse_ref('project_template_tasks.project_task_11')
        self.template_parent_task_0 = self.browse_ref('project_template_tasks_planning_improved.template_parent_task_0')
        self.template_parent_task_1 = self.browse_ref('project_template_tasks_planning_improved.template_parent_task_1')
        self.template_parent_task_2 = self.browse_ref('project_template_tasks_planning_improved.template_parent_task_2')
        self.template_parent_task_3 = self.browse_ref('project_template_tasks_planning_improved.template_parent_task_3')

    def test_10_template_tasks_planning_improved(self):
        """Testing the generation of tasks from templates, with correct links"""

        new_project = self.env['project.project'].create({
            'name': "Test project (Template Tasks)"
        })
        self.assertEqual(len(new_project.use_task_type_ids), 4)
        self.assertIn(self.stage0, new_project.use_task_type_ids)
        self.assertIn(self.stage1, new_project.use_task_type_ids)
        self.assertIn(self.stage2, new_project.use_task_type_ids)
        self.assertIn(self.stage3, new_project.use_task_type_ids)

        # Synchronizing stage 1
        self.stage1.with_context(project_id=new_project.id).synchronize_default_tasks()
        domain_stage1 = [('is_template', '=', False),
                         ('project_id', '=', new_project.id),
                         ('stage_id', '=', self.stage1.id)]
        parent_task_1 = self.env['project.task'].search(domain_stage1 + [('generated_from_template_id', '=', self.template_parent_task_1.id)])
        task2 = self.env['project.task'].search(domain_stage1 + [('generated_from_template_id', '=', self.template_task2.id)])
        task3 = self.env['project.task'].search(domain_stage1 + [('generated_from_template_id', '=', self.template_task3.id)])
        task4 = self.env['project.task'].search(domain_stage1 + [('generated_from_template_id', '=', self.template_task4.id)])
        task5 = self.env['project.task'].search(domain_stage1 + [('generated_from_template_id', '=', self.template_task5.id)])
        task6 = self.env['project.task'].search(domain_stage1 + [('generated_from_template_id', '=', self.template_task6.id)])
        task7 = self.env['project.task'].search(domain_stage1 + [('generated_from_template_id', '=', self.template_task7.id)])
        self.assertEqual(len(parent_task_1), 1)
        self.assertEqual(len(task2), 1)
        self.assertEqual(len(task3), 1)
        self.assertEqual(len(task4), 1)
        self.assertEqual(len(task5), 1)
        self.assertEqual(len(task6), 1)
        self.assertEqual(len(task7), 1)
        self.assertEqual(task2.parent_task_id, parent_task_1)
        self.assertEqual(task3.parent_task_id, parent_task_1)
        self.assertEqual(task4.parent_task_id, parent_task_1)
        self.assertEqual(task5.parent_task_id, parent_task_1)
        self.assertEqual(task6.parent_task_id, parent_task_1)
        self.assertEqual(task7.parent_task_id, parent_task_1)
        # Tasks of stage 1 should not be linked with other tasks, but only with eachother
        self.assertFalse(parent_task_1.previous_task_ids)
        self.assertFalse(parent_task_1.next_task_ids)
        self.assertFalse(task2.previous_task_ids)
        self.assertEqual(task2.next_task_ids, task4)
        self.assertFalse(task3.previous_task_ids)
        self.assertFalse(task3.next_task_ids)
        self.assertEqual(task4.previous_task_ids, task2)
        self.assertFalse(task4.next_task_ids)
        self.assertFalse(task5.previous_task_ids)
        self.assertFalse(task5.next_task_ids)
        self.assertFalse(task6.previous_task_ids)
        self.assertEqual(task6.next_task_ids, task7)
        self.assertEqual(task7.previous_task_ids, task6)
        self.assertFalse(task7.next_task_ids)

        # Synchronizing stage 0
        self.stage0.with_context(project_id=new_project.id).synchronize_default_tasks()
        domain_stage0 = [('is_template', '=', False),
                         ('project_id', '=', new_project.id),
                         ('stage_id', '=', self.stage0.id)]
        parent_task_0 = self.env['project.task'].search(domain_stage0 + [('generated_from_template_id', '=', self.template_parent_task_0.id)])
        task1 = self.env['project.task'].search(domain_stage0 + [('generated_from_template_id', '=', self.template_task1.id)])
        self.assertEqual(len(parent_task_0), 1)
        self.assertEqual(len(task1), 1)
        self.assertEqual(task1.parent_task_id, parent_task_0)
        # Task of stage 0 should be linked with tasks of stage 1
        self.assertFalse(parent_task_0.previous_task_ids)
        self.assertEqual(parent_task_0.next_task_ids, parent_task_1)
        self.assertFalse(task1.previous_task_ids)
        self.assertEqual(len(task1.next_task_ids), 3)
        self.assertIn(task2, task1.next_task_ids)
        self.assertIn(task3, task1.next_task_ids)
        self.assertIn(task6, task1.next_task_ids)

        # Synchronizing stage 3
        self.stage3.with_context(project_id=new_project.id).synchronize_default_tasks()
        domain_stage3 = [('is_template', '=', False),
                         ('project_id', '=', new_project.id),
                         ('stage_id', '=', self.stage3.id)]
        parent_task_3 = self.env['project.task'].search(domain_stage3 + [('generated_from_template_id', '=', self.template_parent_task_3.id)])
        task10 = self.env['project.task'].search(domain_stage3 + [('generated_from_template_id', '=', self.template_task10.id)])
        task11 = self.env['project.task'].search(domain_stage3 + [('generated_from_template_id', '=', self.template_task11.id)])
        self.assertEqual(len(parent_task_0), 1)
        self.assertEqual(len(task10), 1)
        self.assertEqual(len(task11), 1)
        self.assertEqual(task10.parent_task_id, parent_task_3)
        self.assertEqual(task11.parent_task_id, parent_task_3)
        # Task of stage 3 should not be linked
        self.assertFalse(parent_task_3.previous_task_ids)
        self.assertFalse(parent_task_3.next_task_ids)
        self.assertFalse(task10.previous_task_ids)
        self.assertFalse(task10.next_task_ids)
        self.assertFalse(task11.previous_task_ids)
        self.assertFalse(task11.next_task_ids)

        # Synchronizing stage 2
        self.stage2.with_context(project_id=new_project.id).synchronize_default_tasks()
        domain_stage2 = [('is_template', '=', False),
                         ('project_id', '=', new_project.id),
                         ('stage_id', '=', self.stage2.id)]
        parent_task_2 = self.env['project.task'].search(domain_stage2 + [('generated_from_template_id', '=', self.template_parent_task_2.id)])
        task8 = self.env['project.task'].search(domain_stage2 + [('generated_from_template_id', '=', self.template_task8.id)])
        task9 = self.env['project.task'].search(domain_stage2 + [('generated_from_template_id', '=', self.template_task9.id)])
        self.assertEqual(len(parent_task_2), 1)
        self.assertEqual(len(task8), 1)
        self.assertEqual(len(task9), 1)
        self.assertEqual(task8.parent_task_id, parent_task_2)
        self.assertEqual(task9.parent_task_id, parent_task_2)
        # Task of stage 2 should be linked with tasks which are before and after
        self.assertEqual(parent_task_2.previous_task_ids, parent_task_1)
        self.assertEqual(parent_task_2.next_task_ids, parent_task_3)
        self.assertEqual(len(task8.previous_task_ids), 3)
        self.assertIn(task4, task8.previous_task_ids)
        self.assertIn(task5, task8.previous_task_ids)
        self.assertIn(task7, task8.previous_task_ids)
        self.assertEqual(len(task8.next_task_ids), 2)
        self.assertIn(task10, task8.next_task_ids)
        self.assertIn(task11, task8.next_task_ids)
        self.assertFalse(task9.previous_task_ids)
        self.assertEqual(len(task9.next_task_ids), 2)
        self.assertIn(task10, task9.next_task_ids)
        self.assertIn(task11, task9.next_task_ids)
