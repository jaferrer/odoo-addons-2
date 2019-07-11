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


class TestSchedulerAsyncMoves(common.TransactionCase):

    def setUp(self):
        super(TestSchedulerAsyncMoves, self).setUp()
        self.test_product = self.browse_ref('product.product_product_3')
        self.location = self.browse_ref('stock.stock_location_stock')
        self.move = self.env['stock.move'].create({
            'name': u"Test move (Scheduler Async)",
            'product_id': self.test_product.id,
            'location_id': self.location.id,
            'location_dest_id': self.location.id,
            'product_uom_qty': 1,
            'product_uom': self.test_product.uom_id.id,
        })
        self.assertEqual(self.move.state, 'draft')

    def get_jobs_for_move(self, move):
        job_uuid = move.confirm_job_uuid
        return job_uuid and self.env['queue.job'].search([('uuid', '=', job_uuid)]) or self.env['queue.job']

    def test_10_scheduler_async_proc_create_job(self):
        """Check that moves are confirmed by a job"""
        self.env['procurement.order'].with_context(jobify=True).run_confirm_moves()
        self.assertTrue(self.move.confirm_job_uuid)
        job = self.get_jobs_for_move(self.move)
        self.assertEqual(len(job), 1)
        self.assertEqual(job.state, 'pending')

    def test_20_scheduler_async_proc_do_not_recreate_job(self):
        """Check that a new job can not be created for a move linked to a running job"""
        self.env['procurement.order'].with_context(jobify=True).run_confirm_moves()
        self.assertTrue(self.move.confirm_job_uuid)
        init_job = self.get_jobs_for_move(self.move)
        self.assertEqual(len(init_job), 1)
        self.assertEqual(init_job.state, 'pending')

        # Job in state pending
        self.env['procurement.order'].with_context(jobify=True).run_confirm_moves()
        self.assertTrue(self.move.confirm_job_uuid)
        job = self.get_jobs_for_move(self.move)
        self.assertEqual(job, init_job)
        self.assertEqual(job.state, 'pending')

        # Job in state enqueued
        init_job.state = 'enqueued'
        self.env['procurement.order'].with_context(jobify=True).run_confirm_moves()
        self.assertTrue(self.move.confirm_job_uuid)
        job = self.get_jobs_for_move(self.move)
        self.assertEqual(job, init_job)
        self.assertEqual(job.state, 'enqueued')

        # Job in state started
        init_job.state = 'started'
        self.env['procurement.order'].with_context(jobify=True).run_confirm_moves()
        self.assertTrue(self.move.confirm_job_uuid)
        job = self.get_jobs_for_move(self.move)
        self.assertEqual(job, init_job)
        self.assertEqual(job.state, 'started')

    def test_30_scheduler_async_proc_recreate_job_if_needed(self):
        """Check that a new job can not be created for a move linked to a failed or done job"""
        self.env['procurement.order'].with_context(jobify=True).run_confirm_moves()
        self.assertTrue(self.move.confirm_job_uuid)
        init_job = self.get_jobs_for_move(self.move)
        self.assertEqual(len(init_job), 1)
        self.assertEqual(init_job.state, 'pending')

        # Case when inked job is failed
        init_job.state = 'failed'
        self.env['procurement.order'].with_context(jobify=True).run_confirm_moves()
        self.assertTrue(self.move.confirm_job_uuid)
        job = self.get_jobs_for_move(self.move)
        self.assertEqual(len(job), 1)
        self.assertNotEqual(job, init_job)
        self.assertEqual(self.move.confirm_job_uuid, job.uuid)
        self.assertEqual(job.state, 'pending')

        # Case when inked job is done
        init_job = job
        init_job.state = 'done'
        self.env['procurement.order'].with_context(jobify=True).run_confirm_moves()
        self.assertTrue(self.move.confirm_job_uuid)
        job = self.get_jobs_for_move(self.move)
        self.assertEqual(len(job), 1)
        self.assertNotEqual(job, init_job)
        self.assertEqual(self.move.confirm_job_uuid, job.uuid)
        self.assertEqual(job.state, 'pending')

    def test_40_scheduler_async_proc_check_job(self):
        """Check that a job to confirm a move works as expected"""

        # Proc with no job uuid
        session = ConnectorSession.from_env(self.env)
        confirm_moves(session, 'stock.move', self.move.ids, dict(self.env.context))
        self.assertEqual(self.move.state, 'confirmed')

        # Proc with correct job uuid
        self.move.write({'picking_id': False, 'state': 'draft'})
        self.env['procurement.order'].with_context(jobify=True).run_confirm_moves()
        self.assertTrue(self.move.confirm_job_uuid)
        init_job = self.get_jobs_for_move(self.move)
        self.assertEqual(len(init_job), 1)
        self.assertEqual(init_job.state, 'pending')
        session = ConnectorSession.from_env(self.env)
        with session.change_context(job_uuid=init_job.uuid):
            confirm_moves(session, 'stock.move', self.move.ids, dict(self.env.context))
        self.assertEqual(self.move.state, 'confirmed')

        # Proc with incorrect job uuid
        self.move.write({'picking_id': False, 'state': 'draft'})
        self.env['procurement.order'].with_context(jobify=True).run_confirm_moves()
        self.assertTrue(self.move.confirm_job_uuid)
        init_job = self.get_jobs_for_move(self.move)
        self.assertEqual(len(init_job), 1)
        self.assertEqual(init_job.state, 'pending')
        session = ConnectorSession.from_env(self.env)
        with session.change_context(job_uuid='wrong_job_uuid'):
            with self.assertRaises(RetryableJobError):
                confirm_moves(session, 'stock.move', self.move.ids, dict(self.env.context))
        self.assertEqual(self.move.state, 'draft')
