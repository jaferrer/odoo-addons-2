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

from odoo.tests import common
from odoo import models


class ModelInheritMailThread(models.BaseModel):
    _name = 'model.inherit.mail.thread'
    _inherit = 'mail.thread'
    _auto = True


class TestMailNoAutofollow(common.TransactionCase):

    def setUp(self):
        super(TestMailNoAutofollow, self).setUp()
        self.partner_id = self.ref('base.res_partner_1')
        self.user_id = self.ref('base.partner_demo')
        # Force the register of the monkeyPatch
        self.env['mail_thread.extend']._register_hook()

    def tearDown(self):
        self.env['mail_thread.extend']._unregister_hook()
        super(TestMailNoAutofollow, self).tearDown()

    def test_10_post_no_autofollow(self):
        """Check that only users are subscribed."""
        ModelInheritMailThread._build_model(self.registry, self.cr)
        testmodel = self.env['model.inherit.mail.thread']
        testmodel._prepare_setup()
        testmodel._setup_base(False)
        testmodel._setup_fields(True)
        testmodel._setup_complete()
        testmodel.with_context(todo=[])._auto_init()
        mt_object = self.env['model.inherit.mail.thread'].create({})
        wizard = self.env['mail.compose.message'].create({
            'partner_ids': [(6, 0, [self.partner_id, self.user_id])],
            'subject': "Test email",
            'body': "This is a test email",
            'model': 'model.inherit.mail.thread',
            'res_id': mt_object.id,
        })
        wizard.with_context(mail_post_autofollow=True).send_mail()
        self.assertIn(self.user_id, mt_object.message_partner_ids.ids)
        self.assertNotIn(self.partner_id, mt_object.message_partner_ids.ids)
