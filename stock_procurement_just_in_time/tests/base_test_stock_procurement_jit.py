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

from openerp.tests import common
from openerp.tools.misc import frozendict


class BaseTestStockProcurementJIT(common.TransactionCase):

    def setUp(self):
        super(BaseTestStockProcurementJIT, self).setUp()
        self.env.context = frozendict(dict(self.env.context, check_product_qty=False))
        self.test_product = self.browse_ref("stock_procurement_just_in_time.product_test_product")
        self.test_product2 = self.browse_ref("stock_procurement_just_in_time.product_test_product2")
        self.test_product3 = self.browse_ref("stock_procurement_just_in_time.product_test_product3")
        self.test_product4 = self.browse_ref("stock_procurement_just_in_time.product_test_product4")
        self.warehouse_orderpoint1 = self.browse_ref("stock_procurement_just_in_time.warehouse_orderpoint1")
        self.stock_location_orig = self.browse_ref("stock_procurement_just_in_time.stock_location_orig")
        self.location_a = self.browse_ref("stock_procurement_just_in_time.stock_location_a")
        self.location_b = self.browse_ref("stock_procurement_just_in_time.stock_location_b")
        self.location_inv = self.browse_ref("stock.location_inventory")
        self.product_uom_unit_id = self.ref("product.product_uom_unit")
        self.unit = self.browse_ref('product.product_uom_unit')
        self.stock = self.browse_ref('stock.stock_location_stock')
        self.customer = self.browse_ref('stock.stock_location_customers')
        self.supplier = self.browse_ref('stock.stock_location_suppliers')
        self.rule_move = self.browse_ref('stock_procurement_just_in_time.rule_move')
        # Compute parent left and right for location so that test don't fail
        self.env['stock.location']._parent_store_compute()
        # Configure cancelled moves/procs deletion
        wizard = self.env['stock.config.settings'].create({'relative_stock_delta': 10,
                                                           'absolute_stock_delta': 1,
                                                           'consider_end_contract_effect': True})
        wizard.execute()
        self.env['queue.job'].search([]).write({'state': 'done'})

        for location in self.env['stock.location'].search([]):
            self.env['stock.location.scheduler.sequence'].create({'location_id': location.id,
                                                                  'name': 0})

    def process_orderpoints(self, product_ids=None):
        """Function to call the scheduler without needing connector to work."""
        if not product_ids:
            product_ids = [self.test_product.id, self.test_product3.id, self.test_product4.id]
        existing_controller_lines = self.env['stock.scheduler.controller'].search([])
        self.env['procurement.order'].with_context(compute_product_ids=product_ids,
                                                   compute_all_products=False,
                                                   jobify=False)._procure_orderpoint_confirm(run_procurements=False,
                                                                                             run_moves=False)
        orderpoints = self.env['stock.warehouse.orderpoint'].search([('product_id', 'in', product_ids)])
        controller_lines = self.env['stock.scheduler.controller']. \
            search([('id', 'not in', existing_controller_lines.ids)])
        self.assertEqual(len(orderpoints), len(controller_lines) - 1)
        controller_lines_data = [(line.orderpoint_id, line.product_id, line.location_id,
                                  line.location_sequence, line.run_procs, line.done)
                                 for line in controller_lines]
        for op in orderpoints:
            for sequence in op.stock_scheduler_sequence_ids:
                self.assertIn((op, op.product_id, op.location_id, sequence.name,
                               False, False), controller_lines_data)

        self.env['stock.scheduler.controller'].update_scheduler_controller(jobify=False, run_procurements=False)
        self.env['stock.scheduler.controller'].update_scheduler_controller(jobify=False, run_procurements=False)
        orderpoints = self.env['stock.warehouse.orderpoint'].search([('product_id', 'in', product_ids)])
        controller_lines = self.env['stock.scheduler.controller']. \
            search([('id', 'not in', existing_controller_lines.ids)])
        self.assertEqual(len(orderpoints), len(controller_lines) - 1)
        controller_lines_data = [(line.orderpoint_id, line.product_id, line.location_id, line.location_sequence,
                                  line.run_procs, line.job_uuid, line.done)
                                 for line in controller_lines]
        for op in orderpoints:
            for sequence in op.stock_scheduler_sequence_ids:
                self.assertIn((op, op.product_id, op.location_id, sequence.name,
                               False, str(op.id), True), controller_lines_data)
