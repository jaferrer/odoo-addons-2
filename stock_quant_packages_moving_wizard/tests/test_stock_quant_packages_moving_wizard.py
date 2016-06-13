# -*- coding: utf8 -*-
#
# Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class TestStockQuantPackagesMovingWizard(common.TransactionCase):
    def setUp(self):
        super(TestStockQuantPackagesMovingWizard, self).setUp()

        self.package_h = self.browse_ref("stock_quant_packages_moving_wizard.package_header")
        self.package_c = self.browse_ref("stock_quant_packages_moving_wizard.package_child")

        self.location_source = self.browse_ref("stock_quant_packages_moving_wizard.stock_location_source")
        self.location_dest = self.browse_ref("stock_quant_packages_moving_wizard.stock_location_dest")

        self.quant_h_a = self.browse_ref("stock_quant_packages_moving_wizard.quant_header_a")
        self.quant_h_b = self.browse_ref("stock_quant_packages_moving_wizard.quant_header_b")

        self.quant_c_a = self.browse_ref("stock_quant_packages_moving_wizard.quant_child_a")
        self.quant_c_b = self.browse_ref("stock_quant_packages_moving_wizard.quant_child_b")
        self.quant_c_c = self.browse_ref("stock_quant_packages_moving_wizard.quant_child_c")

        self.quant_w_a = self.browse_ref("stock_quant_packages_moving_wizard.quant_a")
        self.quant_w_b = self.browse_ref("stock_quant_packages_moving_wizard.quant_b")

        self.picking_type = self.browse_ref("stock.picking_type_internal")

    def test_10_move_packages(self):
        self.assertEqual(self.package_h.location_id, self.location_source)
        self.assertEqual(self.package_c.location_id, self.location_source)
        self.assertEqual(self.quant_h_a.location_id, self.location_source)
        self.assertEqual(self.quant_h_a.location_id, self.location_source)
        self.assertEqual(self.quant_c_a.location_id, self.location_source)
        self.assertEqual(self.quant_c_b.location_id, self.location_source)
        self.assertEqual(self.quant_c_c.location_id, self.location_source)

        do_move_w = self.env['stock.quant.package.move'].with_context(active_ids=[self.package_h.id]).create({
            'global_dest_loc': self.location_dest.id,
            'picking_type_id': self.picking_type.id,
            'is_manual_op': False
        })
        do_move_w.do_detailed_transfer()

        pack_h = self.browse_ref("stock_quant_packages_moving_wizard.package_header")
        pack_c = self.browse_ref("stock_quant_packages_moving_wizard.package_child")

        quant_1 = self.browse_ref("stock_quant_packages_moving_wizard.quant_header_a")
        quant_2 = self.browse_ref("stock_quant_packages_moving_wizard.quant_header_b")

        quant_3 = self.browse_ref("stock_quant_packages_moving_wizard.quant_child_a")
        quant_4 = self.browse_ref("stock_quant_packages_moving_wizard.quant_child_b")
        quant_5 = self.browse_ref("stock_quant_packages_moving_wizard.quant_child_c")

        self.assertEqual(pack_h.location_id, self.location_dest)
        self.assertEqual(pack_c.location_id, self.location_dest)
        self.assertEqual(quant_1.location_id, self.location_dest)
        self.assertEqual(quant_2.location_id, self.location_dest)
        self.assertEqual(quant_3.location_id, self.location_dest)
        self.assertEqual(quant_4.location_id, self.location_dest)
        self.assertEqual(quant_5.location_id, self.location_dest)

    def test_20_move_simple_quants(self):
        self.assertEqual(self.quant_w_a.location_id, self.location_source)
        self.assertEqual(self.quant_w_b.location_id, self.location_source)

        do_move_w = self.env['stock.quant.move'].with_context(active_ids=[self.quant_w_a.id, self.quant_w_b.id]).create(
            {
                'global_dest_loc': self.location_dest.id,
                'picking_type_id': self.picking_type.id,
                'is_manual_op': False
            })
        do_move_w.do_transfer()

        quant_1 = self.browse_ref("stock_quant_packages_moving_wizard.quant_a")
        quant_2 = self.browse_ref("stock_quant_packages_moving_wizard.quant_b")

        self.assertEqual(quant_1.location_id, self.location_dest)
        self.assertEqual(quant_2.location_id, self.location_dest)

