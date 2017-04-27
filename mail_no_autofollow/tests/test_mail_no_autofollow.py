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
from openerp import models

class TestModelInheritMailThread(models.TransientModel):
    _name = 'test.model.inherit.mail.thread'
    _inherit = 'mail.thread'

class TestMailNoAutofollow(common.TransactionCase):

    def setUp(self):
        super(TestMailNoAutofollow, self).setUp()
        self.partner_id = self.ref('base.res_partner_1')
        self.user_id = self.ref('base.user_demo_res_partner')

    def test_10_post_no_autofollow(self):
        TestModelInheritMailThread._build_model(self.registry, self.cr)
        """Check that only users are subscribed."""
        mt_object = self.env['mail.thread'].create({})
        wizard = self.env['mail.compose.message'].create({
            'partner_ids': [(6, 0, [self.partner_id, self.user_id])],
            'subject': "Test email",
            'body': "This is a test email",
            'model': 'mail.thread',
            'res_id': mt_object.id,
        })
        wizard.with_context(mail_post_autofollow=True).send_mail()
        self.assertIn(self.user_id, mt_object.message_follower_ids.ids)
        self.assertNotIn(self.partner_id, mt_object.message_follower_ids.ids)