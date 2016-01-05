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

from openerp import fields, models, api, _

class stock_transfer_details_select(models.TransientModel):
    _inherit = "stock.transfer_details"

    @api.multi
    def open_select_wizard(self):
        return {
            'name': _('Select Operations'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'stock.transfer_details_items',
            'target': 'popup',
            'views': [(False, 'tree')],
            'domain': [('transfer_id','=',self[0].id)],
            'flags': {
                'search_view': True,
                # 'action_buttons': True,
                'sidebar': True,
            },
            'context': self.env.context,
        }

class stock_transfer_details_items_select(models.TransientModel):
    _inherit = 'stock.transfer_details_items'

    @api.multi
    def delete_lines(self):
        """Deletes the selected item lines and closes the child popup."""
        if len(self) > 0:
            self.unlink()
            return False

    @api.multi
    def keep_only_lines(self):
        """Deletes all item lines that are not selected and closes the child popup."""
        if len(self) > 0:
            transfer_id = self[0].transfer_id
            to_delete_lines = self.search([('transfer_id','=',transfer_id.id)]) - self
            to_delete_lines.unlink()
            return False
