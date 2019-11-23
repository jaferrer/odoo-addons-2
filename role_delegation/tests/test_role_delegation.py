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
from datetime import date
from freezegun import freeze_time

from odoo import fields
from odoo.tests import common


class TestRoleDelegation(common.TransactionCase):
    def setUp(self):
        super(TestRoleDelegation, self).setUp()

        self.source_role = self.env['res.users.role'].create({
            'name': u"Source role",
        })
        self.target_role = self.env['res.users.role'].create({
            'name': u"Target role",
        })
        self.source_user = self.env['res.users'].create({
            'name': u"Delegation source",
            'login': u"Delegation source",
            'role_line_ids': [(0, 0, {'role_id': self.source_role.id})],
        })
        self.target_user = self.env['res.users'].create({
            'name': u"Delegation target",
            'login': u"Delegation target",
            'role_line_ids': [(0, 0, {'role_id': self.target_role.id})],
        })

        self.delegation = self.env['res.users.role.delegation'].create({
            'user_id': self.source_user.id,
            'target_id': self.target_user.id,
            'date_from': date(2012, 12, 7),
            'date_to': date(2012, 12, 21)
        })

    def test_00_role_is_delegated(self):
        """ When a user delegates their role to another user, the targer user temporarily gets the original user role
        """
        self.assertItemsEqual(self.target_user.role_line_ids.mapped('role_id'), [self.source_role, self.target_role])
        role_line = self.env['res.users.role.line'].search([
            ('role_id', '=', self.source_role.id),
            ('user_id', '=', self.target_user.id)
        ])

        self.assertEqual(len(role_line), 1)
        self.assertEqual(role_line.date_from, fields.Date.to_string(date(2012, 12, 7)))
        self.assertEqual(role_line.date_to, fields.Date.to_string(date(2012, 12, 21)))

    def test_01_not_allowed_before(self):
        """ Before the delegation start, the source user is not in the target user's allowed_user_ids """
        with freeze_time('2012-11-7'):
            self.assertNotIn(self.source_user, self.target_user.allowed_user_ids)
            self.assertIn(self.target_user, self.target_user.allowed_user_ids)

    def test_02_allowed_during(self):
        """ In the delegation's boundaries, the source user is included in the target user's allowed_user_ids """
        with freeze_time('2012-12-8'):
            self.assertIn(self.source_user, self.target_user.allowed_user_ids)
            self.assertIn(self.target_user, self.target_user.allowed_user_ids)

    def test_03_not_allowed_after(self):
        """ After the delegation end, the source user is not in the target user's allowed_user_ids """
        with freeze_time('2012-12-31'):
            self.assertNotIn(self.source_user, self.target_user.allowed_user_ids)
            self.assertIn(self.target_user, self.target_user.allowed_user_ids)

    def test_10_date_change_is_propagated_in_roles(self):
        """ When one date of the delegation is changed, the role attribution boundary changes as well """
        role_line = self.env['res.users.role.line'].search([
            ('role_id', '=', self.source_role.id),
            ('user_id', '=', self.target_user.id)
        ])

        self.delegation.write({'date_from': date(2012, 12, 8)})
        self.assertEqual(role_line.date_from, fields.Date.to_string(date(2012, 12, 8)))

        self.delegation.write({'date_to': date(2012, 12, 31)})
        self.assertEqual(role_line.date_to, fields.Date.to_string(date(2012, 12, 31)))

    def test_20_role_delegation_deletion_works(self):
        """ When a role delegation is deleted, all the associated role are removed from the target user and they lose
        the original user in their allowed_user_ids
        """
        self.delegation.unlink()
        self.assertItemsEqual(self.target_user.role_line_ids.mapped('role_id'), [self.target_role])
        with freeze_time('2012-12-8'):
            self.assertNotIn(self.source_user, self.target_user.allowed_user_ids)
            self.assertIn(self.target_user, self.target_user.allowed_user_ids)
