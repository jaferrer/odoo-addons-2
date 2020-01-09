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
import odoo
from odoo import api
from odoo.exceptions import AccessError
from odoo.tests import common

from .field_permission_tester_example_class import FieldPermissionsTester


class GenericTestFieldPermissions(common.SavepointCase):
    @classmethod
    def _init_test_model(cls, model_cls):
        """ Closely inspired from OCA/base_multi_company
        https://github.com/OCA/multi-company/blob/10.0/base_multi_company/tests/test_multi_company_abstract.py

        Builds a model
        :param model_cls: model to initialize
        :return: instance of the model
        """
        registry = cls.env.registry
        cr = cls.env.cr
        inst = model_cls._build_model(registry, cr)
        model = cls.env[model_cls._name].with_context(todo=[])
        model._prepare_setup()
        model._setup_base(partial=False)
        model._setup_fields(partial=False)
        model._setup_complete()
        model._auto_init()
        model.init()
        model._auto_end()
        cls.test_model_record = cls.env['ir.model'].search([
            ('name', '=', model._name),
        ])
        cls.env['ir.model.access'].create({
            'name': model_cls._name.replace('.', '_') + u"_base_access_rule",
            'model_id': cls.test_model_record.id,
            'group_id': cls.env.ref('base.group_user').id,
            'perm_read': True,
            'perm_write': True,
            'perm_create': True,
            'perm_unlink': True,
        })
        return inst

    @classmethod
    def setUpClass(cls):
        super(GenericTestFieldPermissions, cls).setUpClass()
        cls.env.registry.enter_test_mode()
        cls._init_test_model(FieldPermissionsTester)
        cls.test_model = cls.env[FieldPermissionsTester._name]

    @classmethod
    def _clean_test_model_remains(cls):
        """ Dirty hack not to throw a warning from the test model's lack of access rules.

        We tried to completely remove the test model but did not succeed.
        So we created a new cursor that won't be rollbacked with the rest of the tests, and used it to create permanent
        access rules for the test model.

        Thankfully, it only affects tests db, and won't be present in the regular one.

        TODO Find out how to properly remove the test model
        """
        registry = odoo.registry(odoo.tools.config['db_name'])
        with registry.cursor() as cr:
            env = api.Environment(cr, odoo.SUPERUSER_ID, {})
            model_id = env['ir.model'].search([
                ('name', '=', FieldPermissionsTester._name),
            ]).id
            env['ir.model.access'].create({
                'name': FieldPermissionsTester._name.replace('.', '_') + u"_base_access_rule",
                'model_id': model_id,
                'group_id': env.ref('base.group_user').id,
                'perm_read': True,
                'perm_write': True,
                'perm_create': True,
                'perm_unlink': True,
            })
            # domain = [('model', '=', FieldPermissionsTester._name)]

            # env[FieldPermissionsTester._name].search([]).unlink()
            # env['ir.model.fields'].with_context(_force_unlink=True).search(domain).unlink()
            # env['ir.model'].with_context(_force_unlink=True).search(domain).unlink()
            registry.clear_caches()
            env.reset()

    @classmethod
    def tearDownClass(cls):
        cls.env.registry.leave_test_mode()
        super(GenericTestFieldPermissions, cls).tearDownClass()

        # Now, delete the records of the test model in order to avoid any issues with missing related ir.model.access
        cls._clean_test_model_remains()

    def setUp(self):
        super(GenericTestFieldPermissions, self).setUp()
        self._tester = self.test_model.create({
            'boolean_forbidden_field': 1337,
            'boolean_allowed_field': 1337,
            'function_secured_field': 1337,
            'method_secured_field': 1337,
            'key_to_method_secured_field': False,
        })
        self.gp_user = self.env['res.users'].create({
            'name': u"Cobaye",
            'login': u"Cobaye",
        })


class TestFieldReadPermission(GenericTestFieldPermissions):
    def test_00_read_boolean_forbidden_field(self):
        self.assertEqual(self._tester.boolean_forbidden_field, 1337)
        self.assertEqual(self._tester.sudo(self.gp_user).boolean_forbidden_field, False)

    def test_01_read_boolean_allowed_field(self):
        self.assertEqual(self._tester.boolean_allowed_field, 1337)
        self.assertEqual(self._tester.sudo(self.gp_user).boolean_allowed_field, 1337)

    def test_10_read_function_secured_field_reject(self):
        self.assertEqual(self._tester.function_secured_field, 1337)
        self.assertEqual(self._tester.sudo(self.gp_user).function_secured_field, False)
        self.assertEqual(self._tester.sudo(self.gp_user).with_context(allowed_to_read_the_field=False).
                         function_secured_field, False)

    def test_11_read_function_secured_field_accept(self):
        self.assertEqual(self._tester.function_secured_field, 1337)
        self.assertEqual(self._tester.sudo(self.gp_user).function_secured_field, False)
        self.assertEqual(self._tester.sudo(self.gp_user).with_context(allowed_to_read_the_field=True).
                         function_secured_field, 1337)

    def test_20_read_method_secured_field_reject(self):
        self.assertEqual(self._tester.key_to_method_secured_field, False)
        self.assertEqual(self._tester.method_secured_field, 1337)
        self.assertEqual(self._tester.sudo(self.gp_user).method_secured_field, False)

    def test_21_read_method_secured_field_reject(self):
        self.assertEqual(self._tester.key_to_method_secured_field, False)
        self.assertEqual(self._tester.method_secured_field, 1337)
        self.assertEqual(self._tester.sudo(self.gp_user).method_secured_field, False)
        self.assertEqual(self._tester.sudo(self.gp_user).with_context(allowed_to_read_the_field=True).
                         method_secured_field, False)
        self._tester.key_to_method_secured_field = True
        self.env.invalidate_all()
        self.assertEqual(self._tester.sudo(self.gp_user).with_context(allowed_to_read_the_field=True).
                         method_secured_field, 1337)


class TestFieldWritePermission(GenericTestFieldPermissions):
    def test_00_write_boolean_forbidden_field(self):
        self.assertEqual(self._tester.boolean_forbidden_field, 1337)
        self._tester.boolean_forbidden_field = 1994
        self.assertEqual(self._tester.boolean_forbidden_field, 1994)
        with self.assertRaises(AccessError):
            self._tester.sudo(self.gp_user).boolean_forbidden_field = 2012
        self.assertEqual(self._tester.boolean_forbidden_field, 1994)

    def test_01_write_boolean_allowed_field(self):
        self.assertEqual(self._tester.boolean_allowed_field, 1337)
        self._tester.sudo(self.gp_user).boolean_allowed_field = 1994
        self.assertEqual(self._tester.boolean_allowed_field, 1994)

    def test_10_write_function_secured_field_reject(self):
        self.assertEqual(self._tester.function_secured_field, 1337)
        with self.assertRaises(AccessError):
            self._tester.sudo(self.gp_user).with_context(allowed_to_write_the_field=False).function_secured_field = 1994
        self.assertEqual(self._tester.function_secured_field, 1337)

    def test_11_write_function_secured_field_accept(self):
        self.assertEqual(self._tester.function_secured_field, 1337)
        self._tester.sudo(self.gp_user).with_context(allowed_to_write_the_field=True).function_secured_field = 1994
        self.assertEqual(self._tester.function_secured_field, 1994)

    def test_20_write_method_secured_field_reject(self):
        self.assertEqual(self._tester.key_to_method_secured_field, False)
        self.assertEqual(self._tester.method_secured_field, 1337)
        with self.assertRaises(AccessError):
            self._tester.sudo(self.gp_user).with_context(allowed_to_write_the_field=False).method_secured_field = 1994
        self.assertEqual(self._tester.method_secured_field, 1337)

    def test_21_write_method_secured_field_reject(self):
        self.assertEqual(self._tester.key_to_method_secured_field, False)
        self.assertEqual(self._tester.method_secured_field, 1337)
        self._tester.key_to_method_secured_field = True
        self._tester.sudo(self.gp_user).with_context(allowed_to_write_the_field=True).method_secured_field = 1994
        self.assertEqual(self._tester.method_secured_field, 1994)
