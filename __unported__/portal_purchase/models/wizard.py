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
    def get_purchase_sale_groups(self):
        portal_purchase_group = self.env.ref('portal_purchase.group_portal_purchase')
        portal_sale_group = self.env.ref('portal_purchase.group_portal_sale')
        if not portal_purchase_group:
            raise UserError(_("Impossible to find the purchase portal group."))
        if not portal_sale_group:
            raise UserError(_("Impossible to find the sale portal group."))
        return portal_purchase_group, portal_sale_group

    @api.multi
    def get_groups_to_add_or_remove(self, force_group=False):
        portal_purchase_group, portal_sale_group = self.get_purchase_sale_groups()
        list_groups = [portal_purchase_group, portal_sale_group]
        if force_group and force_group not in list_groups:
            list_groups += [force_group]
        return list_groups

    @api.multi
    def remove_useless_groups(self):
        self.ensure_one()
        portal_purchase_group, portal_sale_group = self.get_purchase_sale_groups()
        if not self.partner_id.supplier:
            self.user_id.write({'groups_id': [(3, portal_purchase_group.id)]})
        if not self.partner_id.customer:
            self.user_id.write({'groups_id': [(3, portal_sale_group.id)]})

    @api.multi
    def action_apply(self):
        error_msg = self.get_error_messages()
        if error_msg:
            raise UserError( "\n\n".join(error_msg))
        for wizard_user in self.sudo().with_context(active_test=False):
            portal = wizard_user.wizard_id.portal_id
            list_groups = self.get_groups_to_add_or_remove(force_group=portal)
            user = wizard_user.partner_id.user_ids and wizard_user.partner_id.user_ids[0] or False
            if wizard_user.partner_id.email != wizard_user.email:
                wizard_user.partner_id.write({'email': wizard_user.email})
            if wizard_user.in_portal:
                # create a user if necessary, and make sure it is in the portal group
                if not user:
                    company_id = wizard_user.partner_id.company_id.id
                    user_id = wizard_user.sudo().with_context(company_id=company_id)._create_user()
                else:
                    user_id = user.id
                wizard_user.write({'user_id': user_id})
                if (not wizard_user.user_id.active) or (portal not in wizard_user.user_id.groups_id):
                    wizard_user.user_id.write({'active': True, 'groups_id': [(4, portal.id)]})
                    # prepare for the signup process
                    wizard_user.user_id.partner_id.signup_prepare()
                    wizard_user._send_email()
                wizard_user.refresh()
                for group in list_groups:
                    if group not in wizard_user.user_id.groups_id:
                        wizard_user.user_id.write({'groups_id': [(4, group.id)]})
                wizard_user.remove_useless_groups()
            else:
                # remove the user (if it exists) from the portal group
                if user and (portal in user.groups_id):
                    # if user belongs to portal only, deactivate it
                    dict_modifications = {'groups_id': [(3, group.id) for group in list_groups]}
                    if len(user.groups_id) <= 1:
                        dict_modifications['active'] = False
                    user.write(dict_modifications)
