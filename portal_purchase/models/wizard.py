# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api, _
from openerp.exceptions import UserError


class PortalPurchasePortalWizard(models.TransientModel):
    _inherit = 'portal.wizard.user'

    @api.multi
    def action_apply(self):
        error_msg = self.get_error_messages()
        if error_msg:
            raise UserError( "\n\n".join(error_msg))
        portal_purchase_group = self.env['res.groups'].search([]). \
            filtered(lambda group: group.get_external_id().get(group.id) == 'portal_purchase.group_portal_purchase')
        portal_sale_group = self.env['res.groups'].search([]). \
            filtered(lambda group: group.get_external_id().get(group.id) == 'portal_purchase.group_portal_sale')
        if not portal_purchase_group:
            raise UserError(_("Impossible to find the purchase portal group."))
        if not portal_sale_group:
            raise UserError(_("Impossible to find the sale portal group."))
        for wizard_user in self.sudo().with_context(active_test=False):
            portal = wizard_user.wizard_id.portal_id
            user = wizard_user.partner_id.user_ids and wizard_user.partner_id.user_ids[0] or False
            if wizard_user.partner_id.email != wizard_user.email:
                wizard_user.partner_id.write({'email': wizard_user.email})
            if wizard_user.in_portal:
                # create a user if necessary, and make sure it is in the portal group
                if not user:
                    user_id = wizard_user.sudo()._create_user()
                else:
                    user_id = user.id
                wizard_user.write({'user_id': user_id})
                if (not wizard_user.user_id.active) or (portal not in wizard_user.user_id.groups_id):
                    wizard_user.user_id.write({'active': True, 'groups_id': [(4, portal.id)]})
                    # prepare for the signup process
                    wizard_user.user_id.partner_id.signup_prepare()
                    wizard_user._send_email()
                wizard_user.refresh()
                wizard_user.user_id.write({'groups_id': [(3, portal_purchase_group.id), (3, portal_sale_group.id)]})
                if wizard_user.partner_id.supplier and portal_purchase_group not in wizard_user.user_id.groups_id:
                    wizard_user.user_id.write({'groups_id': [(4, portal_purchase_group.id)]})
                if wizard_user.partner_id.customer and portal_sale_group not in wizard_user.user_id.groups_id:
                    wizard_user.user_id.write({'groups_id': [(4, portal_sale_group.id)]})
            else:
                # remove the user (if it exists) from the portal group
                if user and (portal in user.groups_id):
                    # if user belongs to portal only, deactivate it
                    if len(user.groups_id) <= 1:
                        user.write({'groups_id': [(3, portal.id),
                                                  (3, portal_purchase_group.id),
                                                  (3, portal_sale_group.id)],
                                    'active': False})
                    else:
                        user.write({'groups_id': [(3, portal.id),
                                                  (3, portal_purchase_group.id),
                                                  (3, portal_sale_group.id)]})
