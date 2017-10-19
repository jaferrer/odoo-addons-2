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

from openerp.exceptions import UserError
from openerp import fields, models, api
from openerp.tools.translate import _


class PurchaseOrderGroup(models.TransientModel):
    _name = "purchase.order.group"
    _description = "Purchase Order Merge"

    merge_different_dates = fields.Boolean(string="Merge purchase order lines",
                                           help="It will merge the lines anyway. For instance, you could lose the "
                                                "differences in required dates or unit prices between lines of same "
                                                "product.", default=True)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """
         Changes the view dynamically
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return: New arch of view.
        """
        res = super(PurchaseOrderGroup, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                              submenu=False)
        if self.env.context.get('active_model', '') == 'purchase.order' and len(self.env.context['active_ids']) < 2:
            raise UserError(_('Please select multiple order to merge in the list view.'))
        return res

    @api.multi
    def merge_orders(self):
        """
             To merge similar type of purchase orders. self.ids is not used, but active_ids instead.

        """
        orders = self.env['purchase.order'].search([('id', 'in', self.env.context.get('active_ids', []))])
        allorders = orders.do_merge()

        return {
            'domain': "[('id','in', [" + ','.join(map(str, allorders.keys())) + "])]",
            'name': _('Purchase Orders'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
