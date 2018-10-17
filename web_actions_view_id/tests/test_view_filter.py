# -*- coding: utf-8 -*-
from openerp.tests import common


class TestViewFilter(common.TransactionCase):

    def setUp(self):
        super(TestViewFilter, self).setUp()
        self.base_view = self.browse_ref("base.view_server_action_tree")
        self.view = self.browse_ref("web_actions_view_id.test_web_action_view_id")
        self.action = self.browse_ref("web_actions_view_id.test_web_action_view_id_act")
        self.ir_value = self.browse_ref("web_actions_view_id.ir_value_test_web_action_view_id_act")

    def test_view_id_fields_view_get(self):
        res = self.env['ir.actions.server'].with_context(view_id_fields_view_get=self.view.id,
                                                         view_type_fields_view_get='tree') \
            .fields_view_get(view_id=self.view.id, toolbar=True)
        self.assertTrue(res['toolbar']['action'])
        self.assertEqual(1, len(res['toolbar']['action']))
        self.assertEqual(res['toolbar']['action'][0]['id'], self.action.id)

    def test_view_id_fields_view_get_no_action(self):
        res = self.env['ir.actions.server'].with_context(view_id_fields_view_get=self.base_view.id,
                                                         view_type_fields_view_get='tree') \
            .fields_view_get(view_id=self.view.id, toolbar=True)
        self.assertFalse(res['toolbar']['action'])

    def test_view_type_fields_view_get(self):
        res = self.env['ir.actions.server'].with_context(view_type_fields_view_get='tree',
                                                         tree_view_ref="web_actions_view_id.test_web_action_view_id") \
            .fields_view_get(view_id=self.view.id, toolbar=True)
        self.assertTrue(res['toolbar']['action'])
        self.assertEqual(1, len(res['toolbar']['action']))
        self.assertEqual(res['toolbar']['action'][0]['id'], self.action.id)

    def test_view_type_fields_view_get_no_action(self):
        res = self.env['ir.actions.server'].with_context(view_type_fields_view_get='tree',
                                                         tree_view_ref="base.view_server_action_tree") \
            .fields_view_get(view_id=self.view.id, toolbar=True)
        self.assertFalse(res['toolbar']['action'])
