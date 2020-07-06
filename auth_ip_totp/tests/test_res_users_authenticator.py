# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import mock
from odoo.tests.common import TransactionCase

MOCK_PATH = 'odoo.addons.auth_ip_totp.models.res_users_authenticator.pyotp'


class TestResUsersAuthenticator(TransactionCase):

    def _new_authenticator(self, extra_values=None):
        base_values = {
            'name': 'Test Name',
            'secret_key': 'Test Key',
            'user_id': self.env.ref('base.user_root').id,
        }
        if extra_values is not None:
            base_values.update(extra_values)

        return self.env['res.users.authenticator'].create(base_values)

    def test_check_has_user(self):
        """Should delete record when it no longer has a user_id"""
        test_auth = self._new_authenticator()
        test_auth.user_id = False

        self.assertFalse(test_auth.exists())

    def test_validate_conf_code_empty_recordset(self):
        """Should return False if recordset is empty"""
        test_auth = self.env['res.users.authenticator']

        self.assertFalse(test_auth.validate_conf_code('Test Code'))

    @mock.patch(MOCK_PATH)
    def test_validate_conf_code_match(self, pyotp_mock):
        """Should return True if code matches at least one record in set"""
        test_auth = self._new_authenticator()
        test_auth_2 = self._new_authenticator({'name': 'Test Name 2'})
        test_set = test_auth + test_auth_2

        pyotp_mock.TOTP().verify.side_effect = (True, False)
        self.assertTrue(test_set.validate_conf_code('Test Code'))
        pyotp_mock.TOTP().verify.side_effect = (True, True)
        self.assertTrue(test_set.validate_conf_code('Test Code'))

    @mock.patch(MOCK_PATH)
    def test_validate_conf_code_no_match(self, pyotp_mock):
        """Should return False if code does not match any records in set"""
        test_auth = self._new_authenticator()
        pyotp_mock.TOTP().verify.return_value = False

        self.assertFalse(test_auth.validate_conf_code('Test Code'))

    @mock.patch(MOCK_PATH)
    def test_validate_conf_code_pyotp_use(self, pyotp_mock):
        """Should call PyOTP 2x/record with correct arguments until match"""
        test_auth = self._new_authenticator()
        test_auth_2 = self._new_authenticator({
            'name': 'Test Name 2',
            'secret_key': 'Test Key 2',
        })
        test_auth_3 = self._new_authenticator({
            'name': 'Test Name 3',
            'secret_key': 'Test Key 3',
        })
        test_set = test_auth + test_auth_2 + test_auth_3
        pyotp_mock.TOTP().verify.side_effect = (False, True, True)
        pyotp_mock.reset_mock()
        test_set.validate_conf_code('Test Code')

        pyotp_calls = [
            mock.call('Test Key'),
            mock.call().verify('Test Code'),
            mock.call('Test Key 2'),
            mock.call().verify('Test Code'),
        ]
        self.assertEqual(pyotp_mock.TOTP.mock_calls, pyotp_calls)
