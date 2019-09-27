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
from .base_test_stock_procurement_jit import BaseTestStockProcurementJIT
from ..stock_procurement_jit import ForbiddenCancelProtectedProcurement


class TestStockProcurementJIT(BaseTestStockProcurementJIT):

    def test_10_not_protected_procs(self):
        """Cancel a not protected procurement with the scheduler"""
        procs = self._create_first_proc()
        self.warehouse_orderpoint1.write({'product_min_qty': 0, 'product_max_qty': 0})
        self.process_orderpoints(self.test_product.ids)
        procs2 = self.env['procurement.order'].search([('location_id', '=', self.location_b.id),
                                                       ('product_id', '=', self.test_product.id),
                                                       ('state', '!=', 'cancel')],
                                                      order='date_planned, product_id')
        self.assertTrue(not any(procs2.mapped('protected_against_scheduler')))
        self.assertEqual(len(procs2), 4)
        self.assertEqual([2, 6, 2, 10], procs2.mapped('product_qty'))
        self.assertFalse(procs.exists())

    def test_11_protected_procs(self):
        """Cancel a protected procurement with the scheduler"""
        procs = self._create_first_proc()
        self.warehouse_orderpoint1.write({'product_min_qty': 0, 'product_max_qty': 0})
        procs.write({'protected_against_scheduler': True})
        self.process_orderpoints(self.test_product.ids)
        self.assertTrue(procs.exists())
        self._assert_proc_1(procs)

    def test_20_not_protected_procs(self):
        """Cancel a not protected procurement with the scheduler"""
        procs = self._create_first_proc()
        procs.cancel()
        self.assertEqual(procs.state, 'cancel')
        self.warehouse_orderpoint1.write({'product_min_qty': 0, 'product_max_qty': 0})
        self.process_orderpoints(self.test_product.ids)
        procs2 = self.env['procurement.order'].search([('location_id', '=', self.location_b.id),
                                                       ('product_id', 'in', [self.test_product.id]),
                                                       ('state', '!=', 'cancel')],
                                                      order='date_planned, product_id')
        self.assertTrue(not any(procs2.mapped('protected_against_scheduler')))
        self.assertEqual(len(procs2), 4)
        self.assertEqual([2, 6, 2, 10], procs2.mapped('product_qty'))
        self.assertTrue(procs.exists())

    def test_21_not_protected_procs(self):
        """Cancel a not protected procurement with the scheduler"""
        procs = self._create_first_proc()
        procs.write({'protected_against_scheduler': True})
        procs.cancel()
        self.assertEqual(procs.state, 'cancel')
        self.warehouse_orderpoint1.write({'product_min_qty': 0, 'product_max_qty': 0})
        self.process_orderpoints(self.test_product.ids)
        procs2 = self.env['procurement.order'].search([('location_id', '=', self.location_b.id),
                                                       ('product_id', 'in', [self.test_product.id]),
                                                       ('state', '!=', 'cancel')],
                                                      order='date_planned, product_id')
        self.assertTrue(not any(procs2.mapped('protected_against_scheduler')))
        self.assertEqual(len(procs2), 4)
        self.assertEqual([2, 6, 2, 10], procs2.mapped('product_qty'))
        self.assertTrue(procs.exists())

    def test_30_cancel_procs_just_in_time(self):
        """Cancel a not protected procurement with the scheduler"""
        procs = self._create_first_proc()
        result = procs.cancel_procs_just_in_time(25, 15)
        self.assertEqual(10, result)

    def test_31_cancel_procs_just_in_time(self):
        procs = self._create_first_proc()
        procs.write({'protected_against_scheduler': True})
        result = procs.cancel_procs_just_in_time(15, 25)
        self.assertEqual(15, result)

    def test_40_check_can_be_canceled(self):
        """Cancel a not protected procurement with the scheduler"""
        procs = self._create_first_proc()
        result = procs.check_can_be_canceled(raise_error=False)
        self.assertTrue(result)
        procs.write({'protected_against_scheduler': True})
        result = procs.check_can_be_canceled(raise_error=False)
        self.assertTrue(result)
        result = procs.with_context(is_scheduler=False).check_can_be_canceled(raise_error=False)
        self.assertTrue(result)
        result = procs.with_context(is_scheduler=True).check_can_be_canceled(raise_error=False)
        self.assertFalse(result)

        with self.assertRaises(ForbiddenCancelProtectedProcurement):
            procs.with_context(is_scheduler=True).check_can_be_canceled()

    def _create_first_proc(self):
        self.warehouse_orderpoint1.write({'product_min_qty': 0, 'product_max_qty': 200})
        procs = self.env['procurement.order'].search([('location_id', '=', self.location_b.id),
                                                      ('product_id', 'in', [self.test_product.id]),
                                                      ('state', '!=', 'cancel')])
        self.assertFalse(procs)
        self.process_orderpoints(self.test_product.ids)
        procs = self.env['procurement.order'].search([('location_id', '=', self.location_b.id),
                                                      ('product_id', 'in', [self.test_product.id]),
                                                      ('state', '!=', 'cancel')],
                                                     order='date_planned, product_id')
        self._assert_proc_1(procs)
        self.assertFalse(procs.protected_against_scheduler)
        return procs

    def _assert_proc_1(self, procs):
        self.assertEqual(len(procs), 1)
        self.assertEqual(procs.state, 'running')
        self.assertEqual(202, procs.product_qty)
        self.assertEqual("2015-03-15", procs.date_planned[:10])

