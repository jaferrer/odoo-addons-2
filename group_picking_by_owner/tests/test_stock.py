# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class TestStock(common.TransactionCase):
    def setUp(self):
        super(TestStock, self).setUp()
        self.picking_type = self.env.ref('group_picking_by_owner.default_picking_type')
        self.move1 = self.env.ref('group_picking_by_owner.move1')
        self.move2 = self.env.ref('group_picking_by_owner.move2')
        self.partner1 = self.env.ref('group_picking_by_owner.partner1')
        self.partner2 = self.env.ref('group_picking_by_owner.partner2')

    def test_00_group_by_owner_when_same_owner(self):
        self.assertFalse(self.move1.picking_id)
        self.picking_type.group_picking_by_owner = True
        self.move1.restrict_partner_id = self.partner1
        self.move2.restrict_partner_id = self.partner1
        self.move1._picking_assign()
        self.move2._picking_assign()
        self.assertTrue(self.move1.picking_id)
        self.assertEqual(self.move1.picking_id, self.move2.picking_id)

    def test_01_group_by_owner_when_diff_owners(self):
        self.assertFalse(self.move1.picking_id)
        self.assertFalse(self.move2.picking_id)
        self.picking_type.group_picking_by_owner = True
        self.move1.restrict_partner_id = self.partner1
        self.move2.restrict_partner_id = self.partner2
        self.move1._picking_assign()
        self.move2._picking_assign()
        self.assertTrue(self.move1.picking_id)
        self.assertTrue(self.move2.picking_id)
        self.assertNotEqual(self.move1.picking_id, self.move2.picking_id)

    def test_10_no_grouping_when_same_owners(self):
        self.assertFalse(self.move1.picking_id)
        self.picking_type.group_picking_by_owner = False
        self.move1.restrict_partner_id = self.partner1
        self.move2.restrict_partner_id = self.partner1
        self.move1._picking_assign()
        self.move2._picking_assign()
        self.assertTrue(self.move1.picking_id)
        self.assertEqual(self.move1.picking_id, self.move2.picking_id)

    def test_11_no_grouping_when_diff_owners(self):
        self.assertFalse(self.move1.picking_id)
        self.picking_type.group_picking_by_owner = False
        self.move1.restrict_partner_id = self.partner1
        self.move2.restrict_partner_id = self.partner2
        self.move1._picking_assign()
        self.move2._picking_assign()
        self.assertTrue(self.move1.picking_id)
        self.assertEqual(self.move1.picking_id, self.move2.picking_id)
