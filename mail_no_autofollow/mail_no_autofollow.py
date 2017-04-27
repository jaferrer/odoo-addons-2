# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp.addons.mail.models.mail_thread import MailThread
from openerp import models, api


class BaseModelExtend(models.AbstractModel):
    _name = 'mail_thread.extend'

    message_subscribe_origin = MailThread.message_subscribe

    def _register_hook(self, cr):
        @api.cr_uid_ids_context
        def ugly_override_message_subscribe(self, cr, uid, ids, partner_ids=None, channel_ids=None, subtype_ids=None,
                                            force=True, context=None):
            print partner_ids
            user_ids = self.pool['res.users'].search(cr, uid, [('partner_id', 'in', partner_ids)])
            partner_ids = [u.partner_id.id for u in self.pool['res.users'].browse(cr, uid, user_ids)]
            print partner_ids
            return BaseModelExtend.message_subscribe_origin(self, cr, uid, ids,
                                                            partner_ids=partner_ids,
                                                            channel_ids=channel_ids,
                                                            subtype_ids=subtype_ids,
                                                            force=force,
                                                            context=context)

        MailThread.message_subscribe = ugly_override_message_subscribe
        return super(BaseModelExtend, self)._register_hook(cr)
