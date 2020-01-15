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

from odoo.tests import common
from .fields_tester_example_class import BinaryFieldTester


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
        return inst

    @classmethod
    def setUpClass(cls):
        super(GenericTestFieldPermissions, cls).setUpClass()
        cls.env.registry.enter_test_mode()
        cls._init_test_model(BinaryFieldTester)
        cls.test_model = cls.env[BinaryFieldTester._name]

    @classmethod
    def tearDownClass(cls):
        cls.env.registry.leave_test_mode()
        super(GenericTestFieldPermissions, cls).tearDownClass()

    def test_00_no_name_binary_field(self):
        record = self.env[BinaryFieldTester._name].create({
            'no_name_binary': u"SGVsbG8gd29ybGQgIQ==\n",
        })

        related_attachment = self.env['ir.attachment'].search([
            ('res_model', '=', BinaryFieldTester._name),
            ('res_field', '=', 'no_name_binary'),
            ('res_id', '=', record.id)
        ])
        self.assertEqual(related_attachment.name, 'no_name_binary')

    def test_01_default_name_binary_field(self):
        record = self.env[BinaryFieldTester._name].create({
            'default_name_binary': u"SGVsbG8gd29ybGQgIQ==\n",
            'default_name_binary_fname': u"hello_world.txt",
        })

        related_attachment = self.env['ir.attachment'].search([
            ('res_model', '=', BinaryFieldTester._name),
            ('res_field', '=', 'default_name_binary'),
            ('res_id', '=', record.id)
        ])
        self.assertEqual(related_attachment.name, u"hello_world.txt")

    def test_02_custom_name_binary_field(self):
        record = self.env[BinaryFieldTester._name].create({
            'custom_name_binary': u"SGVsbG8gd29ybGQgIQ==\n",
            'custom_name': u"hello_world.txt",
        })

        related_attachment = self.env['ir.attachment'].search([
            ('res_model', '=', BinaryFieldTester._name),
            ('res_field', '=', 'custom_name_binary'),
            ('res_id', '=', record.id)
        ])
        self.assertEqual(related_attachment.name, u"hello_world.txt")
