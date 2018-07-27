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


class TestSchedulerAsyncCheckProcs(common.TransactionCase):

    def setUp(self):
        super(TestSchedulerAsyncCheckProcs, self).setUp()
        self.test_product = self.browse_ref('product.product_product_3')
        self.location = self.browse_ref('stock.stock_location_stock')
        self.proc = self.env['procurement.order'].create({
            'name': u"Test procurement (Scheduler Async)",
            'product_id': self.test_product.id,
            'location_id': self.location.id,
            'product_qty': 1,
            'product_uom': self.test_product.uom_id.id,
        })
        self.assertEqual(self.proc.state, 'confirmed')

    def get_jobs_for_proc(self, proc):
        job_uuid = proc.run_or_confirm_job_uuid
        return job_uuid and self.env['queue.job'].search([('uuid', '=', job_uuid)]) or self.env['queue.job']

    def test_10_scheduler_async_proc_create_job(self):
        """Check that procurements are checked by a job"""
        self.env['procurement.order'].with_context(jobify=True).run_check_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(len(job), 1)
        self.assertEqual(job.state, 'pending')

    def test_20_scheduler_async_proc_do_not_recreate_job(self):
        """Check that a new job can not be created for a procurement linked to a running job"""
        self.env['procurement.order'].with_context(jobify=True).run_check_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        init_job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(len(init_job), 1)
        self.assertEqual(init_job.state, 'pending')

        # Job in state pending
        self.env['procurement.order'].with_context(jobify=True).run_check_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(job, init_job)
        self.assertEqual(job.state, 'pending')

        # Job in state enqueued
        init_job.state = 'enqueued'
        self.env['procurement.order'].with_context(jobify=True).run_check_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(job, init_job)
        self.assertEqual(job.state, 'enqueued')

        # Job in state started
        init_job.state = 'started'
        self.env['procurement.order'].with_context(jobify=True).run_check_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(job, init_job)
        self.assertEqual(job.state, 'started')

    def test_30_scheduler_async_proc_recreate_job_if_needed(self):
        """Check that a new job can not be created for a procurement linked to a failed or done job"""
        self.env['procurement.order'].with_context(jobify=True).run_check_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        init_job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(len(init_job), 1)
        self.assertEqual(init_job.state, 'pending')

        # Case when inked job is failed
        init_job.state = 'failed'
        self.env['procurement.order'].with_context(jobify=True).run_check_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(len(job), 1)
        self.assertNotEqual(job, init_job)
        self.assertEqual(self.proc.run_or_confirm_job_uuid, job.uuid)
        self.assertEqual(job.state, 'pending')

        # Case when inked job is done
        init_job = job
        init_job.state = 'done'
        self.env['procurement.order'].with_context(jobify=True).run_check_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(len(job), 1)
        self.assertNotEqual(job, init_job)
        self.assertEqual(self.proc.run_or_confirm_job_uuid, job.uuid)
        self.assertEqual(job.state, 'pending')
