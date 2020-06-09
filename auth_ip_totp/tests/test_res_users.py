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

from mock import patch
from odoo.exceptions import AccessDenied, ValidationError
from odoo.tests.common import TransactionCase
from ..exceptions import MfaLoginNeeded
from ..models.res_users import JsonSecureCookie
from ..models.res_users_authenticator import ResUsersAuthenticator

MODEL_PATH = 'odoo.addons.auth_ip_totp.models.res_users'
REQUEST_PATH = MODEL_PATH + '.request'


class TestResUsers(TransactionCase):

    def setUp(self):
        super(TestResUsers, self).setUp()

        self.test_model = self.env['res.users']

        self.test_user = self.env.ref('base.user_demo')
        self.test_user.mfa_enabled = False
        self.test_user.authenticator_ids = False
        self.env['res.users.authenticator'].create({
            'name': 'Test Name',
            'secret_key': 'Test Key',
            'user_id': self.test_user.id,
        })
        self.test_user.mfa_authorized = True
        self.test_user.mfa_enabled = True
        self.env['authorized.ip'].create({
            'name': '156.157.158.159',
            'company_id': self.env.user.company_id.id,
        })

    def test_compute_trusted_device_cookie_key_disable_mfa(self):
        """It should clear out existing key when MFA is disabled"""
        self.test_user.mfa_enabled = False

        self.assertFalse(self.test_user.trusted_device_cookie_key)

    def test_compute_trusted_device_cookie_key_enable_mfa(self):
        """It should generate a new key when MFA is enabled"""
        old_key = self.test_user.sudo().trusted_device_cookie_key
        self.test_user.mfa_enabled = False
        self.test_user.mfa_enabled = True

        self.assertNotEqual(self.test_user.trusted_device_cookie_key, old_key)

    def test_build_model_mfa_fields_in_self_writeable_list(self):
        """Should add MFA fields to list of fields users can modify for self"""
        res_users_class = type(self.test_user)
        self.assertIn('mfa_enabled', res_users_class.SELF_WRITEABLE_FIELDS)
        self.assertIn('authenticator_ids', res_users_class.SELF_WRITEABLE_FIELDS)

    def test_check_enabled_with_authenticator_mfa_no_auth(self):
        """Should raise correct error if MFA enabled without authenticators"""
        with self.assertRaisesRegexp(ValidationError, 'locked out'):
            self.test_user.authenticator_ids = False

    def test_check_enabled_with_authenticator_no_mfa_auth(self):
        """Should not raise error if MFA not enabled with authenticators"""
        try:
            self.test_user.mfa_enabled = False
        except ValidationError:
            self.fail('A ValidationError was raised and should not have been.')

    @patch(REQUEST_PATH, new=None)
    def test_check_mfa_without_request(self):
        """It should remove UID from cache if in MFA cache and no request"""
        test_cache = self.test_model._Users__uid_cache[self.env.cr.dbname]
        test_cache[self.env.uid] = 'test'
        self.test_model._mfa_uid_cache[self.env.cr.dbname].add(self.env.uid)
        try:
            self.test_model.check(self.env.cr.dbname, self.env.uid, 'test')
        except AccessDenied:
            pass

        self.assertFalse(test_cache.get(self.env.uid))

    @patch(REQUEST_PATH)
    def test_check_mfa_no_mfa_session(self, request_mock):
        """It should remove UID from cache if MFA cache but no MFA session"""
        request_mock.session = {}
        request_mock.httprequest.remote_addr = '185.104.37.52'
        test_cache = self.test_model._Users__uid_cache[self.env.cr.dbname]
        test_cache[self.env.uid] = 'test'
        self.test_model._mfa_uid_cache[self.env.cr.dbname].add(self.env.uid)
        try:
            self.test_model.check(self.env.cr.dbname, self.env.uid, 'test')
        except AccessDenied:
            pass

        self.assertFalse(test_cache.get(self.env.uid))

    @patch(REQUEST_PATH)
    def test_check_mfa_invalid_mfa_session(self, request_mock):
        """It should remove UID if in MFA cache but invalid MFA session"""
        request_mock.session = {'mfa_login_active': self.env.uid + 1}
        request_mock.httprequest.remote_addr = '185.104.37.52'
        test_cache = self.test_model._Users__uid_cache[self.env.cr.dbname]
        test_cache[self.env.uid] = 'test'
        self.test_model._mfa_uid_cache[self.env.cr.dbname].add(self.env.uid)
        try:
            self.test_model.check(self.env.cr.dbname, self.env.uid, 'test')
        except AccessDenied:
            pass

        self.assertFalse(test_cache.get(self.env.uid))

    def test_check_no_mfa(self):
        """It should not remove UID from cache if not in MFA cache"""
        test_cache = self.test_model._Users__uid_cache[self.env.cr.dbname]
        test_cache[self.env.uid] = 'test'
        self.test_model._mfa_uid_cache[self.env.cr.dbname].clear()
        self.test_model.check(self.env.cr.dbname, self.env.uid, 'test')

        self.assertEqual(test_cache.get(self.env.uid), 'test')

    @patch(REQUEST_PATH)
    def test_check_mfa_valid_session(self, request_mock):
        """It should not remove UID if in MFA cache and valid session"""
        request_mock.session = {'mfa_login_active': self.env.uid}
        test_cache = self.test_model._Users__uid_cache[self.env.cr.dbname]
        test_cache[self.env.uid] = 'test'
        self.test_model._mfa_uid_cache[self.env.cr.dbname].add(self.env.uid)
        self.test_model.check(self.env.cr.dbname, self.env.uid, 'test')

        self.assertEqual(test_cache.get(self.env.uid), 'test')

    def test_check_credentials_mfa_not_enabled(self):
        """Access should be denied if user does not have MFA enabled"""
        self.test_user.mfa_enabled = False

        with self.assertRaises(AccessDenied):
            self.env['res.users'].sudo(self.test_user).check_credentials('invalid')
        with self.assertRaises(AccessDenied):
            self.env['res.users'].sudo(self.test_user).check_credentials('demo')

    def test_check_credentials_mfa_uid_cache(self):
        """It should add user's ID to MFA UID cache if MFA enabled"""
        self.test_model._mfa_uid_cache[self.env.cr.dbname].clear()
        try:
            self.test_model.sudo(self.test_user).check_credentials('invalid')
        except AccessDenied:
            pass

        result_cache = self.test_model._mfa_uid_cache[self.env.cr.dbname]
        self.assertEqual(result_cache, {self.test_user.id})

    @patch(REQUEST_PATH, new=None)
    def test_check_credentials_mfa_and_no_request(self):
        """Should raise correct exception if MFA enabled and no request"""
        with self.assertRaises(AccessDenied):
            self.env['res.users'].sudo(self.test_user).sudo(self.test_user).check_credentials('invalid')
        with self.assertRaises(MfaLoginNeeded):
            self.env['res.users'].sudo(self.test_user).sudo(self.test_user).check_credentials('demo')

    @patch(REQUEST_PATH)
    def test_check_credentials_mfa_login_active(self, request_mock):
        """Should check password if user has finished MFA auth this session"""
        request_mock.session = {'mfa_login_active': self.test_user.id}
        request_mock.httprequest.remote_addr = '185.104.37.52'

        with self.assertRaises(AccessDenied):
            self.env['res.users'].sudo(self.test_user).check_credentials('invalid')
        try:
            self.env['res.users'].sudo(self.test_user).check_credentials('demo')
        except AccessDenied:
            self.fail('An exception was raised with a correct password.')

    @patch(REQUEST_PATH)
    def test_check_credentials_mfa_different_login_active(self, request_mock):
        """Should correctly raise/update if other user finished MFA auth"""
        request_mock.session = {'mfa_login_active': self.test_user.id + 1}
        request_mock.httprequest.cookies = {}
        request_mock.httprequest.remote_addr = '185.104.37.52'

        with self.assertRaises(AccessDenied):
            self.env['res.users'].sudo(self.test_user).check_credentials('invalid')
        self.assertFalse(request_mock.session.get('mfa_login_needed'))
        with self.assertRaises(MfaLoginNeeded):
            self.env['res.users'].sudo(self.test_user).check_credentials('demo')
        self.assertTrue(request_mock.session.get('mfa_login_needed'))

    @patch(REQUEST_PATH)
    def test_check_credentials_mfa_no_device_cookie(self, request_mock):
        """Should correctly raise/update session if MFA and no device cookie"""
        request_mock.session = {'mfa_login_active': False}
        request_mock.httprequest.cookies = {}
        request_mock.httprequest.remote_addr = '185.104.37.52'

        with self.assertRaises(AccessDenied):
            self.env['res.users'].sudo(self.test_user).check_credentials('invalid')
        self.assertFalse(request_mock.session.get('mfa_login_needed'))
        with self.assertRaises(MfaLoginNeeded):
            self.env['res.users'].sudo(self.test_user).check_credentials('demo')
        self.assertTrue(request_mock.session.get('mfa_login_needed'))

    @patch(REQUEST_PATH)
    def test_check_credentials_mfa_corrupted_device_cookie(self, request_mock):
        """Should correctly raise/update session if MFA and corrupted cookie"""
        request_mock.session = {'mfa_login_active': False}
        test_key = 'trusted_devices_%d' % self.test_user.id
        request_mock.httprequest.cookies = {test_key: 'invalid'}
        request_mock.httprequest.remote_addr = '185.104.37.52'

        with self.assertRaises(AccessDenied):
            self.env['res.users'].sudo(self.test_user).check_credentials('invalid')
        self.assertFalse(request_mock.session.get('mfa_login_needed'))
        with self.assertRaises(MfaLoginNeeded):
            self.env['res.users'].sudo(self.test_user).check_credentials('demo')
        self.assertTrue(request_mock.session.get('mfa_login_needed'))

    @patch(REQUEST_PATH)
    def test_check_credentials_mfa_cookie_from_wrong_user(self, request_mock):
        """Should raise and update session if MFA and wrong user's cookie"""
        request_mock.session = {'mfa_login_active': False}
        request_mock.httprequest.remote_addr = '185.104.37.52'
        test_user_2 = self.env['res.users'].sudo().create({
            'name': 'Test User',
            'login': 'test_user',
        })
        test_id_2 = test_user_2.id
        self.env['res.users.authenticator'].create({
            'name': 'Test Name',
            'secret_key': 'Test Key',
            'user_id': test_id_2,
        })
        test_user_2.mfa_authorized = True
        test_user_2.mfa_enabled = True
        secret = test_user_2.trusted_device_cookie_key
        test_device_cookie = JsonSecureCookie({'user_id': test_id_2}, secret)
        test_device_cookie = test_device_cookie.serialize()
        test_key = 'trusted_devices_%d' % self.test_user.id
        request_mock.httprequest.cookies = {test_key: test_device_cookie}

        with self.assertRaises(AccessDenied):
            self.env['res.users'].sudo(self.test_user).check_credentials('invalid')
        self.assertFalse(request_mock.session.get('mfa_login_needed'))
        with self.assertRaises(MfaLoginNeeded):
            self.env['res.users'].sudo(self.test_user).check_credentials('demo')
        self.assertTrue(request_mock.session.get('mfa_login_needed'))

    @patch(REQUEST_PATH)
    def test_check_credentials_mfa_correct_device_cookie(self, request_mock):
        """Should check password if MFA and correct device cookie"""
        request_mock.session = {'mfa_login_active': False}
        request_mock.httprequest.remote_addr = '185.104.37.52'
        secret = self.test_user.trusted_device_cookie_key
        test_device_cookie = JsonSecureCookie(
            {'user_id': self.test_user.id},
            secret,
        )
        test_device_cookie = test_device_cookie.serialize()
        test_key = 'trusted_devices_%d' % self.test_user.id
        request_mock.httprequest.cookies = {test_key: test_device_cookie}

        with self.assertRaises(AccessDenied):
            self.env['res.users'].sudo(self.test_user).check_credentials('invalid')
        self.env['res.users'].sudo(self.test_user).check_credentials('demo')

    def test_validate_mfa_confirmation_code_not_singleton(self):
        """Should raise correct error when recordset is not singleton"""
        test_user_2 = self.env['res.users']
        test_user_3 = self.env.ref('base.public_user')
        test_set = self.test_user + test_user_3

        with self.assertRaisesRegexp(ValueError, 'Expected singleton'):
            test_user_2.validate_mfa_confirmation_code('Test Code')
        with self.assertRaisesRegexp(ValueError, 'Expected singleton'):
            test_set.validate_mfa_confirmation_code('Test Code')

    @patch.object(ResUsersAuthenticator, 'validate_conf_code')
    def test_validate_mfa_confirmation_code_singleton_return(self, mock_func):
        """Should return validate_conf_code() value if singleton recordset"""
        mock_func.return_value = 'Test Result'

        self.assertEqual(
            self.test_user.validate_mfa_confirmation_code('Test Code'),
            'Test Result',
        )

    def test_01_check_mfa_authorized_mfa_enabled(self):
        self.assertTrue(self.test_user.mfa_enabled)
        self.test_user.mfa_authorized = False
        self.assertFalse(self.test_user.mfa_enabled)
        with self.assertRaises(ValidationError):
            self.test_user.mfa_enabled = True

    @patch(REQUEST_PATH)
    def test_02_check_user_from_internal(self, request_mock):
        """User should be able to login without MFA from correct IP"""
        # Assume we have MFA in session to check that our login is not blocked by MFA
        request_mock.session = {'mfa_login_active': True}
        request_mock.httprequest.remote_addr = '156.157.158.159'
        self.test_user.mfa_authorized = False
        self.assertFalse(self.test_user.mfa_enabled)
        self.env['res.users'].sudo(self.test_user).check_credentials('demo')

    @patch(REQUEST_PATH)
    def test_03_check_user_from_internal(self, request_mock):
        """User should be not be able to login without MFA from incorrect IP"""
        # Assume we have MFA in session to check that our login is not blocked by MFA
        request_mock.session = {'mfa_login_active': True}
        request_mock.httprequest.remote_addr = '156.157.158.160'
        self.test_user.mfa_authorized = False
        self.assertFalse(self.test_user.mfa_enabled)
        with self.assertRaises(AccessDenied):
            self.env['res.users'].sudo(self.test_user).check_credentials('demo')

    @patch(REQUEST_PATH)
    def test_04_check_user_from_internal(self, request_mock):
        """User should be not be able to login without MFA (but authorization) from incorrect IP"""
        # Assume we have MFA in session to check that our login is not blocked by MFA
        request_mock.session = {'mfa_login_active': True}
        request_mock.httprequest.remote_addr = '156.157.158.160'
        self.test_user.mfa_enabled = False
        with self.assertRaises(AccessDenied):
            self.env['res.users'].sudo(self.test_user).check_credentials('demo')

    @patch(REQUEST_PATH)
    def test_05_check_user_from_localhost(self, request_mock):
        """User should be able to login from localhost"""
        # Assume we have MFA in session to check that our login is not blocked by MFA
        request_mock.session = {'mfa_login_active': True}
        request_mock.httprequest.remote_addr = '127.0.0.1'
        self.test_user.mfa_enabled = False
        self.env['res.users'].sudo(self.test_user).check_credentials('demo')

    @patch(REQUEST_PATH)
    def test_06_check_admin_login_op_ips(self, request_mock):
        """Admin only should be able to login if there is no ips"""
        # Assume we have MFA in session to check that our login is not blocked by MFA
        request_mock.session = {'mfa_login_active': False}
        request_mock.httprequest.remote_addr = '156.85.123.12'
        self.env.user.mfa_enabled = False
        with self.assertRaises(AccessDenied):
            self.env['res.users'].check_credentials('admin')
        self.test_user.company_id.authorized_ip_ids = False
        self.env['res.users'].check_credentials('admin')
        with self.assertRaises(AccessDenied):
            self.env['res.users'].sudo(self.test_user).check_credentials('demo')
