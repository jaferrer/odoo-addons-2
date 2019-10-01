# -*- coding: utf8 -*-
#
# Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api
from openerp.osv import fields as old_api_fields


class mail_thread(models.Model):
    _inherit = 'mail.thread'

    def _get_followers(self, cr, uid, ids, name, arg, context=None):
        return super(mail_thread, self)._get_followers(cr, uid, ids, name, arg, context=context)

    def _search_followers(self, cr, uid, obj, name, args, context):
        return super(mail_thread, self)._search_followers(cr, uid, obj, name, args, context)

    def _set_followers(self, cr, uid, id, name, value, arg, context=None):
        if context.get('do_not_subscribe_anybody'):
            return
        return super(mail_thread, self)._set_followers(cr, uid, id, name, value, arg, context=context)

    _columns = {
        'message_follower_ids': old_api_fields.function(_get_followers, fnct_inv=_set_followers,
                                                fnct_search=_search_followers, type='many2many', priority=-10,
                                                obj='res.partner', string='Followers', multi='_get_followers'),
    }

    @api.multi
    def message_subscribe(self, partner_ids, subtype_ids=None):
        """ Add partners to the records followers.
        Overridden here to only subscribe users and not external partners."""
        user_partners = self.env['res.users'].search([('partner_id','in',partner_ids)])
        partner_ids = [u.partner_id.id for u in user_partners]
        return super(mail_thread, self).message_subscribe(partner_ids, subtype_ids)
