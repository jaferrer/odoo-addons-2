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
from openerp.addons.scheduler_async.scheduler_async import run_or_check_procurements, confirm_moves
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.exception import RetryableJobError


class TestSchedulerAsyncRunProcs(common.TransactionCase):

    def setUp(self):
        super(TestSchedulerAsyncRunProcs, self).setUp()
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
        """Check that procurements are confirmed by a job"""
        self.env['procurement.order'].with_context(jobify=True).run_confirm_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(len(job), 1)
        self.assertEqual(job.state, 'pending')

    def test_20_scheduler_async_proc_do_not_recreate_job(self):
        """Check that a new job can not be created for a procurement linked to a running job"""
        self.env['procurement.order'].with_context(jobify=True).run_confirm_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        init_job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(len(init_job), 1)
        self.assertEqual(init_job.state, 'pending')

        # Job in state pending
        self.env['procurement.order'].with_context(jobify=True).run_confirm_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(job, init_job)
        self.assertEqual(job.state, 'pending')

        # Job in state enqueued
        init_job.state = 'enqueued'
        self.env['procurement.order'].with_context(jobify=True).run_confirm_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(job, init_job)
        self.assertEqual(job.state, 'enqueued')

        # Job in state started
        init_job.state = 'started'
        self.env['procurement.order'].with_context(jobify=True).run_confirm_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(job, init_job)
        self.assertEqual(job.state, 'started')

    def test_30_scheduler_async_proc_recreate_job_if_needed(self):
        """Check that a new job can not be created for a procurement linked to a failed or done job"""
        self.env['procurement.order'].with_context(jobify=True).run_confirm_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        init_job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(len(init_job), 1)
        self.assertEqual(init_job.state, 'pending')

        # Case when inked job is failed
        init_job.state = 'failed'
        self.env['procurement.order'].with_context(jobify=True).run_confirm_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(len(job), 1)
        self.assertNotEqual(job, init_job)
        self.assertEqual(self.proc.run_or_confirm_job_uuid, job.uuid)
        self.assertEqual(job.state, 'pending')

        # Case when inked job is done
        init_job = job
        init_job.state = 'done'
        self.env['procurement.order'].with_context(jobify=True).run_confirm_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(len(job), 1)
        self.assertNotEqual(job, init_job)
        self.assertEqual(self.proc.run_or_confirm_job_uuid, job.uuid)
        self.assertEqual(job.state, 'pending')

    def test_40_scheduler_async_proc_check_job(self):
        """Check that a job to confirm a procurement works as expected"""

        # Proc with no job uuid
        session = ConnectorSession.from_env(self.env)
        run_or_check_procurements(session, 'procurement.order', [('id', '=', self.proc.id)],
                                  'run', dict(self.env.context))
        self.assertEqual(self.proc.state, 'exception')

        # Proc with correct job uuid
        self.proc.cancel()
        self.proc.reset_to_confirmed()
        self.assertEqual(self.proc.state, 'confirmed')
        self.env['procurement.order'].with_context(jobify=True).run_confirm_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        init_job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(len(init_job), 1)
        self.assertEqual(init_job.state, 'pending')
        session = ConnectorSession.from_env(self.env)
        with session.change_context(job_uuid=init_job.uuid):
            run_or_check_procurements(session, 'procurement.order', [('id', '=', self.proc.id)],
                                      'run', dict(self.env.context))
        self.assertEqual(self.proc.state, 'exception')

        # Proc with incorrect job uuid
        self.proc.cancel()
        self.proc.reset_to_confirmed()
        self.assertEqual(self.proc.state, 'confirmed')
        self.env['procurement.order'].with_context(jobify=True).run_confirm_procurements()
        self.assertTrue(self.proc.run_or_confirm_job_uuid)
        init_job = self.get_jobs_for_proc(self.proc)
        self.assertEqual(len(init_job), 1)
        self.assertEqual(init_job.state, 'pending')
        session = ConnectorSession.from_env(self.env)
        with session.change_context(job_uuid='wrong_job_uuid'):
            with self.assertRaises(RetryableJobError):
                run_or_check_procurements(session, 'procurement.order', [('id', '=', self.proc.id)],
                                          'run', dict(self.env.context))
        self.assertEqual(self.proc.state, 'confirmed')
